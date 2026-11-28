from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import threading
import time
import uuid

from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import database
from engine.index import InvertedIndex
from engine.tfidf import TFIDF
from engine.bm25 import BM25
from engine.text import tokenize

ROOT = Path(__file__).resolve().parents[1]
app = FastAPI(title="Mini Search Engine")
cache = OrderedDict()
lock = threading.RLock()
CACHE_COLLECTIONS = 4


class CollectionInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)


def now():
    return datetime.now(timezone.utc).isoformat()


def check_collection(db, collection_id):
    if not db.execute("SELECT id FROM collections WHERE id=?", (collection_id,)).fetchone():
        raise HTTPException(404, "Collection not found")


def clear_cache(collection_id):
    cache.pop(collection_id, None)


def get_models(db, collection_id):
    if collection_id in cache:
        cache.move_to_end(collection_id)
        return cache[collection_id], None
    rows = db.execute("SELECT id, filename, text FROM documents WHERE collection_id=? ORDER BY id", (collection_id,)).fetchall()
    if not rows:
        return None, None
    documents = {row["id"]: {"title": row["filename"], "text": row["text"]} for row in rows}
    start = time.perf_counter()
    index = InvertedIndex(documents)
    models = {"tfidf": TFIDF(index), "bm25": BM25(index)}
    elapsed = (time.perf_counter() - start) * 1000
    cache[collection_id] = models
    while len(cache) > CACHE_COLLECTIONS:
        cache.popitem(last=False)
    return models, elapsed


def snippet(text, query):
    text = " ".join(text.split())
    positions = [text.lower().find(term) for term in tokenize(query)]
    positions = [position for position in positions if position >= 0]
    start = max(0, min(positions) - 60) if positions else 0
    return ("… " if start else "") + text[start:start + 240] + (" …" if start + 240 < len(text) else "")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/methods")
def methods():
    return {"methods": ["bm25", "tfidf"], "default": "bm25"}


@app.get("/api/collections")
def collections():
    with lock, database.connection() as db:
        return [dict(row) for row in db.execute("SELECT c.*, COUNT(d.id) AS document_count FROM collections c LEFT JOIN documents d ON d.collection_id=c.id GROUP BY c.id ORDER BY c.created_at")]


@app.post("/api/collections", status_code=201)
def create_collection(body: CollectionInput):
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "Collection name cannot be blank")
    record = {"id": uuid.uuid4().hex, "name": name, "created_at": now(), "document_count": 0}
    try:
        with lock, database.connection() as db:
            db.execute("INSERT INTO collections VALUES (?, ?, ?)", (record["id"], name, record["created_at"]))
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "Collection name already exists") from exc
    return record


@app.delete("/api/collections/{collection_id}", status_code=204)
def delete_collection(collection_id: str):
    with lock, database.connection() as db:
        check_collection(db, collection_id)
        paths = [row[0] for row in db.execute("SELECT stored_path FROM documents WHERE collection_id=?", (collection_id,))]
        db.execute("DELETE FROM collections WHERE id=?", (collection_id,))
        db.commit()
        for path in paths:
            Path(path).unlink(missing_ok=True)
        clear_cache(collection_id)


@app.get("/api/collections/{collection_id}/documents")
def documents(collection_id: str):
    with lock, database.connection() as db:
        check_collection(db, collection_id)
        return [dict(row) for row in db.execute("SELECT id, collection_id, filename, size_bytes, num_chars, created_at FROM documents WHERE collection_id=? ORDER BY created_at", (collection_id,))]


@app.post("/api/collections/{collection_id}/documents", status_code=201)
def upload(collection_id: str, files: list[UploadFile]):
    from backend import files as file_tools
    if len(files) > file_tools.MAX_FILES:
        raise HTTPException(413, "Upload at most 20 files at a time")
    uploaded, failed = [], []
    with lock, database.connection() as db:
        check_collection(db, collection_id)
        for item in files:
            name = file_tools.filename(item.filename)
            data = item.file.read(file_tools.MAX_BYTES + 1)
            try:
                text = file_tools.extract(name, data)
            except ValueError as exc:
                failed.append({"filename": name, "error": str(exc)})
                continue
            doc_id = uuid.uuid4().hex
            folder = database.RUNTIME / "uploads" / collection_id
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / (doc_id + Path(name).suffix.lower())
            record = {"id": doc_id, "collection_id": collection_id, "filename": name, "size_bytes": len(data), "num_chars": len(text), "created_at": now()}
            path.write_bytes(data)
            try:
                db.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (doc_id, collection_id, name, str(path), len(data), len(text), text, record["created_at"]))
                db.commit()
            except Exception:
                path.unlink(missing_ok=True)
                raise
            clear_cache(collection_id)
            uploaded.append(record)
    return {"uploaded": uploaded, "failed": failed}


@app.get("/api/collections/{collection_id}/documents/{doc_id}")
def document(collection_id: str, doc_id: str):
    with lock, database.connection() as db:
        row = db.execute("SELECT id, collection_id, filename, size_bytes, num_chars, text, created_at FROM documents WHERE collection_id=? AND id=?", (collection_id, doc_id)).fetchone()
        if row is None:
            raise HTTPException(404, "Document not found")
        return dict(row)


@app.delete("/api/collections/{collection_id}/documents/{doc_id}", status_code=204)
def delete_document(collection_id: str, doc_id: str):
    with lock, database.connection() as db:
        row = db.execute("SELECT stored_path FROM documents WHERE collection_id=? AND id=?", (collection_id, doc_id)).fetchone()
        if row is None:
            raise HTTPException(404, "Document not found")
        db.execute("DELETE FROM documents WHERE id=?", (doc_id,))
        db.commit()
        Path(row[0]).unlink(missing_ok=True)
        clear_cache(collection_id)


@app.get("/api/collections/{collection_id}/search")
def search(collection_id: str, q: str = Query(min_length=1, max_length=500), method: str = "bm25", k: int = Query(default=10, ge=1, le=100)):
    if method not in ("tfidf", "bm25") or not q.strip():
        raise HTTPException(422, "Choose TF-IDF or BM25 and enter a nonempty query")
    with lock, database.connection() as db:
        check_collection(db, collection_id)
        models, build_ms = get_models(db, collection_id)
        start = time.perf_counter()
        ranked = models[method].search(q, k) if models else []
        search_ms = (time.perf_counter() - start) * 1000
        hits = []
        for rank, (doc_id, score) in enumerate(ranked, 1):
            doc = models[method].index.documents[doc_id]
            hits.append({"rank": rank, "doc_id": doc_id, "filename": doc["title"], "score": score, "snippet": snippet(doc["text"], q)})
    return {"query": q, "method": method, "collection_id": collection_id, "total_returned": len(hits), "search_ms": search_ms, "index_build_ms": build_ms, "results": hits}


database.initialize()
app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="frontend")
