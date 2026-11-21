import json
import unittest
from threading import Event
from nexus_study.ollama_client import CancelledError
from nexus_study.retrieval import Chunk
from nexus_study import study

C = [Chunk("physics.txt", "document", "Acceleration equals change in velocity divided by time. Newton's second law states F = ma. " * 4, 1)]


class FakeClient:
    def __init__(self, response="Mock response"):
        self.response = response
        self.calls = []
    def chat(self, model, system, user, **kw):
        self.calls.append((model, system, user, kw))
        return self.response


class TestStudy(unittest.TestCase):
    def test_question_grounded(self):
        client = FakeClient("Acceleration is change in velocity per time [SOURCE 1].")
        reply, docs = study.ask(client, "qwen2.5:3b", C, "What is acceleration?")
        self.assertIn("Acceleration", reply)
        self.assertTrue(docs)
        self.assertIn("[SOURCE 1]", client.calls[0][2])

    def test_question_no_match_skips_model(self):
        client = FakeClient()
        reply, matched = study.ask(client, "test", C, "volcanic eruption")
        self.assertFalse(matched)
        self.assertEqual(len(client.calls), 0)

    def test_parse_json(self):
        self.assertEqual(study.parse_json(' {"cards":[]} '), {"cards": []})
        self.assertEqual(study.parse_json('```json\n{"cards":[]}\n```'), {"cards": []})

    def test_parse_json_bad(self):
        with self.assertRaises(ValueError):
            study.parse_json("not json")

    def test_validate_quiz(self):
        q = {"question":"What is F?", "options":["Force","Speed","Time","Length"],
             "answer_index":0,"explanation":"Source says it", "source":"SOURCE 1"}
        self.assertEqual(len(study.validate_quiz({"questions": [q, q, q]})), 3)

    def test_bool_answer_rejected(self):
        q = {"question":"What is F?", "options":["A","B","C","D"],"answer_index":True}
        with self.assertRaises(ValueError):
            study.validate_quiz({"questions": [q, q, q]})

    def test_bad_quiz_rejected(self):
        with self.assertRaises(ValueError):
            study.validate_quiz({"questions": []})

    def test_validate_flashcards(self):
        cards = [{"front":"A", "back":"B", "source":"SOURCE 1"}] * 4
        self.assertEqual(len(study.validate_flashcards({"cards": cards})), 4)

    def test_bad_flashcards(self):
        with self.assertRaises(ValueError):
            study.validate_flashcards({"cards": [{"front":"a", "back":""}]})

    def test_quiz_requests_json(self):
        q = {"question":"What is F?", "options":["Force","Speed","Time","Length"],
             "answer_index":0,"explanation":"F=ma", "source":"SOURCE 1"}
        client = FakeClient(json.dumps({"questions":[q] * 5}))
        self.assertEqual(len(study.generate_quiz(client,"test",C)),5)
        self.assertTrue(client.calls[0][3]["json_mode"])

    def test_cards_requests_json(self):
        client = FakeClient(json.dumps({"cards":[{"front":"Q","back":"A","source":"SOURCE 1"}] * 8}))
        self.assertEqual(len(study.generate_flashcards(client,"test",C)),8)
        self.assertTrue(client.calls[0][3]["json_mode"])

    def test_single_section_summary(self):
        client = FakeClient("Physics recap [SOURCE 1]")
        s = study.summarize(client,"test",C)
        self.assertIn("Physics recap",s)
        self.assertEqual(len(client.calls),1)

    def test_multi_section_summary(self):
        client = FakeClient("Key facts from source [SOURCE 1].")
        chunks = [Chunk("a.txt",str(i), "Motion and acceleration." * 80,1) for i in range(10)]
        s = study.summarize(client, "test", chunks)
        self.assertIn("STUDY SUMMARY", s)
        self.assertGreater(len(client.calls),2)

    def test_cancel(self):
        e=Event();e.set()
        with self.assertRaises(CancelledError):
            study.summarize(FakeClient(),"test",C,cancel=e)

    def test_empty_summary(self):
        with self.assertRaises(ValueError):
            study.summarize(FakeClient(),"test",[])
