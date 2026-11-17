"""Private local corpus storage and document ingestion."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from docx import Document
from pypdf import PdfReader

from .util import split_chunks

SUPPORTED = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_BYTES = 40 * 1024 * 1024


def home_dir(value: str | None = None) -> Path:
    return Path(value or os.environ.get("DOCUDINO_HOME", Path.home() / ".docudino")).expanduser().resolve()


def read_store(home: Path) -> dict:
    path = home / "corpus.json"
    if not path.exists():
        return {"documents": [], "chunks": []}
    try:
        import json
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and isinstance(value.get("documents"), list) and isinstance(value.get("chunks"), list):
            return value
    except (OSError, ValueError):
        pass
    raise ValueError(f"No pude leer el índice local: {path}. Conservé el archivo sin modificar.")


def save_store(home: Path, data: dict) -> None:
    home.mkdir(parents=True, exist_ok=True)
    try:
        home.chmod(0o700)
    except OSError:
        pass
    path = home / "corpus.json"
    temp = home / "corpus.json.tmp"
    import json
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        temp.chmod(0o600)
    except OSError:
        pass
    temp.replace(path)


def extract(path: Path) -> list[tuple[str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(path)
        return [(f"página {index}", page.extract_text() or "") for index, page in enumerate(reader.pages, 1)]
    if suffix == ".docx":
        doc = Document(path)
        paragraphs = [(f"párrafo {index}", item.text.strip()) for index, item in enumerate(doc.paragraphs, 1) if item.text.strip()]
        for table_index, table in enumerate(doc.tables, 1):
            for row_index, row in enumerate(table.rows, 1):
                text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if text:
                    paragraphs.append((f"tabla {table_index}, fila {row_index}", text))
        return paragraphs
    text = path.read_text(encoding="utf-8", errors="replace")
    return [(f"sección {index}", part.strip()) for index, part in enumerate(text.split("\n\n"), 1) if part.strip()]


def add_file(home: Path, path: Path) -> tuple[str, int, bool]:
    path = path.expanduser().resolve()
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"Formato no soportado: {path.name}. Usa PDF, DOCX, TXT o MD.")
    if not path.is_file():
        raise ValueError(f"No existe el archivo: {path}")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f"{path.name} supera el límite de 40 MB.")
    content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    doc_id = content_hash[:12]
    corpus = read_store(home)
    if any(doc.get("id") == doc_id for doc in corpus["documents"]):
        return doc_id, 0, False
    pages = extract(path)
    chunks = []
    for location, text in pages:
        for part_index, chunk_text in enumerate(split_chunks(text), 1):
            chunk_id = f"{doc_id}-{len(chunks) + 1:04d}"
            chunks.append({"id": chunk_id, "doc_id": doc_id, "name": path.name,
                           "location": location, "part": part_index, "text": chunk_text})
    if not chunks:
        raise ValueError(f"No extraje texto de {path.name}. Si es un PDF escaneado, aplica OCR local primero.")
    corpus["documents"].append({"id": doc_id, "name": path.name, "format": path.suffix.lower(),
                                "sha256": content_hash, "chunks": len(chunks)})
    corpus["chunks"].extend(chunks)
    save_store(home, corpus)
    return doc_id, len(chunks), True


def remove_document(home: Path, doc_id: str) -> bool:
    corpus = read_store(home)
    docs = [doc for doc in corpus["documents"] if doc["id"] != doc_id]
    if len(docs) == len(corpus["documents"]):
        return False
    corpus["documents"] = docs
    corpus["chunks"] = [chunk for chunk in corpus["chunks"] if chunk["doc_id"] != doc_id]
    save_store(home, corpus)
    return True
