from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from docx import Document
from pypdf import PdfWriter
from nexus_study.documents import (
    DocumentError, clean_text, load_document, MAX_FILE_BYTES, MAX_EXTRACTED_CHARS)


class TestDocuments(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, name, contents):
        path = self.root / name
        path.write_bytes(contents)
        return path

    def test_txt(self):
        doc = load_document(self.make("notes.txt", b"Physics: F=ma\n\nAcceleration changes velocity."))
        self.assertEqual(doc.name, "notes.txt")
        self.assertEqual(doc.passages[0].locator, "document")
        self.assertIn("F=ma", doc.passages[0].text)

    def test_markdown(self):
        doc = load_document(self.make("notes.md", b"# Lesson\n\nA concept."))
        self.assertIn("# Lesson", doc.passages[0].text)

    def test_utf16(self):
        doc = load_document(self.make("notes.txt", "café".encode("utf-16")))
        self.assertEqual(doc.passages[0].text, "café")

    def test_cp1252_fallback(self):
        doc = load_document(self.make("notes.txt", "café".encode("cp1252")))
        self.assertEqual(doc.passages[0].text, "café")

    def test_custom_label(self):
        doc = load_document(self.make("notes.txt", b"Original"), "Notes (2).txt")
        self.assertEqual(doc.passages[0].source, "Notes (2).txt")

    def test_docx_paragraphs_and_tables(self):
        word = Document()
        word.add_paragraph("Introduction about cells")
        table = word.add_table(rows=1, cols=2)
        table.cell(0, 0).text = "Nucleus"
        table.cell(0, 1).text = "DNA"
        word.add_paragraph("Conclusion")
        path = self.root / "notes.docx"
        word.save(path)
        text = load_document(path).passages[0].text
        self.assertLess(text.index("Introduction"), text.index("Nucleus"))
        self.assertLess(text.index("Nucleus"), text.index("Conclusion"))
        self.assertIn("Nucleus | DNA", text)

    def test_pdf_with_selectable_text(self):
        # Construct a minimal, standards-compliant text PDF without extra test dependencies.
        stream = b"BT /F1 18 Tf 72 700 Td (Newton second law equals force mass acceleration) Tj ET"
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]
        raw = b"%PDF-1.4\n"
        offsets = []
        for idx, obj in enumerate(objects, 1):
            offsets.append(len(raw))
            raw += f"{idx} 0 obj\n".encode() + obj + b"\nendobj\n"
        xref = len(raw)
        raw += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
        for offset in offsets:
            raw += f"{offset:010d} 00000 n \n".encode()
        raw += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
        doc = load_document(self.make("lesson.pdf", raw))
        self.assertEqual(doc.passages[0].locator, "p. 1")
        self.assertIn("Newton second law", doc.passages[0].text)

    def test_pdf_without_text_is_rejected(self):
        writer = PdfWriter()
        writer.add_blank_page(width=500, height=700)
        path = self.root / "scan.pdf"
        with path.open("wb") as fp:
            writer.write(fp)
        with self.assertRaisesRegex(DocumentError, "No selectable text"):
            load_document(path)

    def test_bad_extension(self):
        with self.assertRaisesRegex(DocumentError, "Supported"):
            load_document(self.make("file.exe", b"abc"))

    def test_empty(self):
        with self.assertRaisesRegex(DocumentError, "no readable text"):
            load_document(self.make("empty.txt", b"   \n "))

    def test_file_size_limit(self):
        path = self.root / "large.txt"
        with path.open("wb") as f:
            f.truncate(MAX_FILE_BYTES + 1)
        with self.assertRaisesRegex(DocumentError, "25 MB"):
            load_document(path)

    def test_text_limit(self):
        path = self.root / "large.txt"
        path.write_text("a" * (MAX_EXTRACTED_CHARS + 1))
        with self.assertRaisesRegex(DocumentError, "450,000"):
            load_document(path)

    def test_clean(self):
        self.assertEqual(clean_text(" hi  there\r\n\n\n\n\nend\0"), "hi there\n\nend")
