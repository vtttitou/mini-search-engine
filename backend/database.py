import sqlite3
from contextlib import contextmanager
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1] / "runtime"


@contextmanager
def connection():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(RUNTIME / "app.db")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize():
    with connection() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS collections (
            id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            collection_id TEXT NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
            filename TEXT NOT NULL, stored_path TEXT NOT NULL,
            size_bytes INTEGER NOT NULL, num_chars INTEGER NOT NULL,
            text TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS documents_collection ON documents(collection_id);
        """)
