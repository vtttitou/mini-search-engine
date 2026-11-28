import io
from pathlib import Path
from pypdf import PdfReader

MAX_BYTES = 10 * 1024 * 1024
MAX_FILES = 20


def filename(name):
    cleaned = Path((name or "unnamed").replace("\\", "/")).name
    return "".join(c for c in cleaned if c.isprintable())[:200] or "unnamed"


def extract(name, data):
    extension = Path(name).suffix.lower()
    if extension not in (".txt", ".pdf"):
        raise ValueError("Only TXT and text-based PDF files are supported")
    if not data or len(data) > MAX_BYTES:
        raise ValueError("File must contain data and be at most 10 MB")
    if extension == ".txt":
        if b"\x00" in data:
            raise ValueError("File looks binary")
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("Save text files as UTF-8") from exc
    else:
        if not data.startswith(b"%PDF-"):
            raise ValueError("File content is not PDF")
        try:
            pdf = PdfReader(io.BytesIO(data))
            if pdf.is_encrypted:
                raise ValueError("Encrypted PDFs are not supported")
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception as exc:
            raise ValueError("Cannot read this PDF; use an unencrypted text-based PDF") from exc
    if not text.strip():
        raise ValueError("No searchable text; scanned PDFs need OCR")
    return text.strip()
