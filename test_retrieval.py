import tempfile
import unittest
from pathlib import Path
from nexus_study.documents import Passage, StudyDocument
from nexus_study.retrieval import build_index, split_passage, retrieve, tokens, representative_chunks, format_sources


class TestRetrieval(unittest.TestCase):
    def test_chunk_length_and_overlap(self):
        p = Passage("notes.pdf", "p. 2", "physics " * 400)
        chunks = split_passage(p, 160, 25)
        self.assertGreater(len(chunks), 4)
        self.assertTrue(all(len(c.text) <= 160 for c in chunks))
        self.assertTrue(all(c.source == "notes.pdf" for c in chunks))

    def test_invalid_overlap(self):
        with self.assertRaises(ValueError):
            split_passage(Passage("a", "doc", "text"), 100, 100)

    def test_relevance(self):
        docs = [StudyDocument(Path("x.txt"), "x.txt", [
            Passage("x.txt", "document", "Mitochondria generate ATP in cells. " * 8),
            Passage("x.txt", "document 2", "The French revolution began in 1789. " * 8)])]
        chunks = build_index(docs)
        found = retrieve(chunks, "What do mitochondria generate?")
        self.assertIn("ATP", found[0].text)

    def test_missing_relevance(self):
        chunks = split_passage(Passage("a", "document", "Cell energy and ATP"))
        self.assertEqual(retrieve(chunks, "volcano eruption lava"), [])

    def test_query_only_stopwords(self):
        chunks = split_passage(Passage("a", "document", "Blue sky"))
        self.assertEqual(retrieve(chunks, "the is of"), [])

    def test_representative_even(self):
        chunks = [split_passage(Passage("a", str(i), "sentence " * 40))[0] for i in range(11)]
        selected = representative_chunks(chunks, 3)
        self.assertEqual([c.locator for c in selected], ["0", "5", "10"])

    def test_sources(self):
        chunks = split_passage(Passage("hello.txt", "document", "A big concept"))
        self.assertIn("[SOURCE 1] hello.txt", format_sources(chunks))

    def test_unicode(self):
        self.assertIn("fizică", tokens("Despre fizică și chimie"))

    def test_empty(self):
        self.assertEqual(build_index([]), [])
        self.assertEqual(representative_chunks([]), [])
