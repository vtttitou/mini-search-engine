import pytest
from fastapi.testclient import TestClient
from backend import app as web
from backend import database


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "RUNTIME", tmp_path / "runtime")
    database.initialize()
    web.cache.clear()
    with TestClient(web.app) as client:
        yield client


def test_upload_search_delete(client):
    cid = client.post("/api/collections", json={"name": "notes"}).json()["id"]
    base = f"/api/collections/{cid}"
    upload = client.post(base + "/documents", files=[("files", ("../../notes.txt", b"apple banana"))]).json()
    doc = upload["uploaded"][0]
    assert doc["filename"] == "notes.txt"
    for method in ("tfidf", "bm25"):
        result = client.get(base + "/search", params={"q": "apple", "method": method}).json()
        assert result["results"][0]["doc_id"] == doc["id"]
    result = client.get(base + "/search", params={"q": "apple"}).json()
    assert result["index_build_ms"] is None
    assert client.get(base + "/documents/" + doc["id"]).json()["text"] == "apple banana"
    client.post(base + "/documents", files=[("files", ("other.txt", b"mango"))])
    assert client.get(base + "/search", params={"q": "mango"}).json()["index_build_ms"] is not None
    client.delete(base + "/documents/" + doc["id"])
    assert client.get(base + "/search", params={"q": "apple"}).json()["results"] == []
    other = client.post("/api/collections", json={"name": "other"}).json()["id"]
    assert client.get(f"/api/collections/{other}/documents/{doc['id']}").status_code == 404
    assert client.get(f"/api/collections/{other}/search", params={"q": "mango"}).json()["results"] == []
    assert client.delete(base).status_code == 204


def test_validation_and_frontend(client):
    assert client.get("/").status_code == 200
    assert client.get("/js/app.js").status_code == 200
    assert client.post("/api/collections", json={"name": " "}).status_code == 422
    cid = client.post("/api/collections", json={"name": "notes"}).json()["id"]
    assert client.post("/api/collections", json={"name": "notes"}).status_code == 409
    base = f"/api/collections/{cid}"
    result = client.post(base + "/documents", files=[("files", ("bad.pdf", b"wrong")), ("files", ("empty.txt", b"")), ("files", ("bad.exe", b"wrong"))]).json()
    assert len(result["failed"]) == 3
    assert client.get(base + "/search", params={"q": "a", "method": "dense"}).status_code == 422


def make_pdf(text: str) -> bytes:
    stream = f'BT /F1 12 Tf 10 50 Td ({text}) Tj ET'.encode()
    objects = [b'<</Type/Catalog/Pages 2 0 R>>', b'<</Type/Pages/Kids[3 0 R]/Count 1>>', b'<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 100]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>', b'<</Length %d>>\nstream\n' % len(stream) + stream + b'\nendstream', b'<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>']
    out, offsets = (bytearray(b'%PDF-1.4\n'), [])
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b'%d 0 obj\n' % i + body + b'\nendobj\n'
    xref = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objects) + 1)
    for off in offsets:
        out += b'%010d 00000 n \n' % off
    out += b'trailer<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF' % (len(objects) + 1, xref)
    return bytes(out)


def test_pdf_and_cache_reload(client):
    cid = client.post("/api/collections", json={"name": "pdf"}).json()["id"]
    base = f"/api/collections/{cid}"
    result = client.post(base + "/documents", files=[("files", ("diet.pdf", make_pdf("Quinoa protein"), "application/pdf"))]).json()
    assert len(result["uploaded"]) == 1
    first = client.get(base + "/search", params={"q": "quinoa"}).json()
    web.cache.clear()
    second = client.get(base + "/search", params={"q": "quinoa"}).json()
    assert first["results"] == second["results"]
    assert second["index_build_ms"] is not None
    assert second["results"][0]["filename"] == "diet.pdf"


def test_limits(client):
    cid = client.post("/api/collections", json={"name": "limits"}).json()["id"]
    base = f"/api/collections/{cid}"
    result = client.post(base + "/documents", files=[("files", ("big.txt", b"a" * (10 * 1024 * 1024 + 1)))]).json()
    assert not result["uploaded"] and result["failed"]
    assert client.get(base + "/search", params={"q": "a", "k": 101}).status_code == 422
