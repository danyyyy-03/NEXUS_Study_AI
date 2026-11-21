"""Read user-selected study documents without modifying them."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re

MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_PDF_PAGES = 400
MAX_EXTRACTED_CHARS = 450_000
SUPPORTED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}


class DocumentError(ValueError):
    pass


@dataclass(frozen=True)
class Passage:
    source: str
    locator: str
    text: str

    @property
    def cite(self) -> str:
        return f"{self.source}, {self.locator}"


@dataclass
class StudyDocument:
    path: Path
    name: str
    passages: list[Passage]

    @property
    def char_count(self) -> int:
        return sum(len(x.text) for x in self.passages)


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{4,}", "\n\n", text).strip()


def _check_size(path: Path) -> None:
    if not path.is_file():
        raise DocumentError("The selected path is not a file.")
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise DocumentError("Supported files: PDF, DOCX, TXT and MD.")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise DocumentError("File exceeds the 25 MB safety limit.")


def load_document(path: str | Path, display_name: str | None = None) -> StudyDocument:
    path = Path(path).expanduser().resolve(strict=True)
    _check_size(path)
    name = display_name or path.name
    suffix = path.suffix.lower()
    passages: list[Passage] = []
    try:
        if suffix == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(str(path), strict=False)
            if reader.is_encrypted:
                try:
                    if reader.decrypt("") == 0:
                        raise DocumentError("Password-protected PDF: unlock it before importing.")
                except DocumentError:
                    raise
                except Exception as exc:
                    raise DocumentError("Password-protected PDF: unlock it before importing.") from exc
            if len(reader.pages) > MAX_PDF_PAGES:
                raise DocumentError(f"PDF exceeds the {MAX_PDF_PAGES}-page limit.")
            total = 0
            for idx, page in enumerate(reader.pages, start=1):
                text = clean_text(page.extract_text() or "")
                if text:
                    total += len(text)
                    if total > MAX_EXTRACTED_CHARS:
                        raise DocumentError("Extracted document text exceeds the 450,000-character limit.")
                    passages.append(Passage(name, f"p. {idx}", text))
        elif suffix == ".docx":
            from docx import Document
            doc = Document(str(path))
            items = []
            # Preserve order of paragraphs and tables where python-docx supports it.
            for block in doc.iter_inner_content():
                if hasattr(block, "rows"):
                    for row in block.rows:
                        cells = [clean_text(cell.text) for cell in row.cells]
                        line = " | ".join(cells)
                        if line.strip(" |"):
                            items.append(line)
                else:
                    if clean_text(block.text):
                        items.append(block.text)
            text = clean_text("\n\n".join(items))
            if len(text) > MAX_EXTRACTED_CHARS:
                raise DocumentError("Extracted document text exceeds the 450,000-character limit.")
            if text:
                passages.append(Passage(name, "document", text))
        else:
            raw = path.read_bytes()
            if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
                text = raw.decode("utf-16")
            else:
                try:
                    text = raw.decode("utf-8-sig")
                except UnicodeDecodeError:
                    text = raw.decode("cp1252")
            text = clean_text(text)
            if len(text) > MAX_EXTRACTED_CHARS:
                raise DocumentError("Document text exceeds the 450,000-character limit.")
            if text:
                passages.append(Passage(name, "document", text))
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError(f"Could not read '{name}': {exc}") from exc
    if not passages:
        if suffix == ".pdf":
            raise DocumentError("No selectable text found. Scanned/image-only PDFs need OCR (not included in v0.1).")
        raise DocumentError("The document has no readable text.")
    return StudyDocument(path=path, name=name, passages=passages)
