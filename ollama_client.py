"""Speak only to a locally running Ollama instance. No paid API key."""
from __future__ import annotations
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from threading import Event
from typing import Callable

BASE_URL = "http://127.0.0.1:11434"


class OllamaError(RuntimeError):
    pass


class CancelledError(RuntimeError):
    pass


def _error_message(exc: Exception) -> str:
    if isinstance(exc, HTTPError):
        try:
            detail = exc.read(2048).decode("utf-8", errors="replace")
            message = json.loads(detail).get("error", detail)
        except Exception:
            message = str(exc)
        return f"Ollama HTTP {exc.code}: {message}"
    if isinstance(exc, (URLError, TimeoutError, socket.timeout, ConnectionError)):
        return "Cannot reach Ollama at 127.0.0.1:11434. Open Ollama and check that it is running."
    return str(exc)


class OllamaClient:
    def __init__(self, base_url: str = BASE_URL):
        # Do not accept arbitrary remote endpoints for this local-only MVP.
        if base_url.rstrip("/") not in (BASE_URL, "http://localhost:11434"):
            raise ValueError("Only local Ollama on port 11434 is supported.")
        self.base_url = BASE_URL

    def models(self) -> list[str]:
        try:
            with urlopen(self.base_url + "/api/tags", timeout=5) as response:
                data = json.load(response)
        except (OSError, ValueError) as exc:
            raise OllamaError(_error_message(exc)) from exc
        return sorted({m.get("name", "") for m in data.get("models", []) if m.get("name")})

    def chat(self, model: str, system: str, user: str, *, json_mode: bool = False,
             cancel: Event | None = None, progress: Callable[[int], None] | None = None) -> str:
        if not model.strip():
            raise OllamaError("Select an Ollama model first.")
        payload = {"model": model, "messages": [
            {"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": True, "options": {"temperature": 0.15, "num_ctx": 8192}}
        if json_mode:
            payload["format"] = "json"
        req = Request(self.base_url + "/api/chat", data=json.dumps(payload).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, method="POST")
        parts: list[str] = []
        try:
            with urlopen(req, timeout=240) as response:
                while True:
                    if cancel is not None and cancel.is_set():
                        raise CancelledError("Request cancelled.")
                    raw = response.readline()
                    if not raw:
                        break
                    data = json.loads(raw.decode("utf-8"))
                    if data.get("error"):
                        raise OllamaError(str(data["error"]))
                    piece = data.get("message", {}).get("content", "")
                    if piece:
                        parts.append(piece)
                        if progress:
                            progress(len(piece))
                    if data.get("done"):
                        break
        except (HTTPError, URLError, TimeoutError, socket.timeout, OSError) as exc:
            raise OllamaError(_error_message(exc)) from exc
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned an invalid response.") from exc
        if cancel is not None and cancel.is_set():
            raise CancelledError("Request cancelled.")
        result = "".join(parts).strip()
        if not result:
            raise OllamaError("The selected model returned no answer. Try a different installed model.")
        return result
