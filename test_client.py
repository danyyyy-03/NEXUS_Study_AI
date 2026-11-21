import io
import json
import unittest
from unittest.mock import patch
from threading import Event
from nexus_study.ollama_client import OllamaClient, OllamaError, CancelledError


class FakeResponse:
    def __init__(self, content):
        self.data = io.BytesIO(content)
    def __enter__(self):
        return self
    def __exit__(self, *_):
        self.data.close()
    def readline(self):
        return self.data.readline()
    def read(self, *args):
        return self.data.read(*args)


class TestClient(unittest.TestCase):
    def test_remote_endpoint_refused(self):
        with self.assertRaises(ValueError):
            OllamaClient("https://example.com")

    def test_models(self):
        raw = json.dumps({"models":[{"name":"qwen2.5:3b"},{"name":"qwen3:8b"}]}).encode()
        with patch("nexus_study.ollama_client.urlopen", return_value=FakeResponse(raw)):
            self.assertEqual(OllamaClient().models(), ["qwen2.5:3b", "qwen3:8b"])

    def test_streaming_response(self):
        lines = [json.dumps({"message":{"content": s},"done": done}) for s,done in (("Hello ",False),("world",False),("",True))]
        data = ("\n".join(lines) + "\n").encode()
        with patch("nexus_study.ollama_client.urlopen", return_value=FakeResponse(data)) as urlopen:
            value = OllamaClient().chat("qwen2.5:3b", "Be helpful", "Hello", json_mode=True)
            self.assertEqual(value,"Hello world")
            req = urlopen.call_args.args[0]
            payload = json.loads(req.data)
            self.assertEqual(payload["format"], "json")
            self.assertEqual(payload["stream"], True)
            self.assertEqual(req.full_url, "http://127.0.0.1:11434/api/chat")

    def test_empty_response(self):
        with patch("nexus_study.ollama_client.urlopen", return_value=FakeResponse(b'{"done":true}\n')):
            with self.assertRaises(OllamaError):
                OllamaClient().chat("model","system","user")

    def test_cancel_before_answer(self):
        cancel=Event();cancel.set()
        with patch("nexus_study.ollama_client.urlopen", return_value=FakeResponse(b'{"message":{"content":"hi"},"done":true}\n')):
            with self.assertRaises(CancelledError):
                OllamaClient().chat("model","system","user",cancel=cancel)

    def test_model_required(self):
        with self.assertRaises(OllamaError):
            OllamaClient().chat(" ","system","user")
