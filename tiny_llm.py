"""
Tiny LLM helper for event-driven, Raspberry Pi-friendly guidance.

This module is intentionally lightweight:
- Optional llama.cpp backend (llama-cpp-python)
- Async inference queue (never blocks camera loop)
- Deterministic fallback hints when model/runtime is unavailable
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Thread
from time import time
from typing import Dict, Optional


@dataclass
class TinyLLMConfig:
    enabled: bool
    model_path: str
    n_ctx: int
    n_threads: int
    max_tokens: int
    temperature: float
    top_p: float
    top_k: int
    repeat_penalty: float


class TinyLLMEngine:
    """Asynchronous tiny LLM wrapper with safe fallback mode."""

    def __init__(self, config: TinyLLMConfig):
        self.config = config
        self._llm = None
        self._status = "Disabled"
        self._tasks: Queue[Dict[str, str]] = Queue(maxsize=8)
        self._results: Queue[Dict[str, str]] = Queue(maxsize=8)
        self._worker = Thread(target=self._worker_loop, daemon=True)
        self._worker.start()

    def update_config(self, config: TinyLLMConfig) -> None:
        self.config = config
        # Force backend reload on next request.
        self._llm = None
        if not self.config.enabled:
            self._status = "Disabled"

    def submit_event(self, event_name: str, detail: str) -> bool:
        try:
            self._tasks.put_nowait({"event": event_name, "detail": detail})
            return True
        except Full:
            return False

    def poll_result(self) -> Optional[Dict[str, str]]:
        try:
            return self._results.get_nowait()
        except Empty:
            return None

    def get_status(self) -> str:
        return self._status

    def _worker_loop(self) -> None:
        while True:
            task = self._tasks.get()
            response = self._generate_response(task["event"], task["detail"])
            result = {
                "event": task["event"],
                "detail": task["detail"],
                "response": response,
                "timestamp": f"{time():.3f}",
            }
            try:
                self._results.put_nowait(result)
            except Full:
                try:
                    self._results.get_nowait()
                except Empty:
                    pass
                self._results.put_nowait(result)

    def _generate_response(self, event_name: str, detail: str) -> str:
        if not self.config.enabled:
            self._status = "Disabled"
            return self._fallback_hint(event_name, detail)

        llm = self._ensure_backend()
        if llm is None:
            return self._fallback_hint(event_name, detail)

        system_prompt = (
            "You are a concise surveillance assistant. "
            "Return one short action-oriented recommendation for real-time tracking."
        )
        user_prompt = f"Event: {event_name}\nContext: {detail}\nGive one concise recommendation."

        try:
            completion = llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
                repeat_penalty=self.config.repeat_penalty,
            )
            message = completion["choices"][0]["message"]["content"].strip()
            self._status = "Ready (LLM)"
            return message or self._fallback_hint(event_name, detail)
        except (ValueError, KeyError, RuntimeError):
            self._status = "Fallback (inference error)"
            return self._fallback_hint(event_name, detail)

    def _ensure_backend(self):
        if self._llm is not None:
            return self._llm

        model_path = Path(self.config.model_path)
        if not model_path.exists():
            self._status = f"Fallback (model missing: {model_path.name})"
            return None

        try:
            from llama_cpp import Llama
        except ImportError:
            self._status = "Fallback (install llama-cpp-python)"
            return None

        try:
            self._llm = Llama(
                model_path=str(model_path),
                n_ctx=self.config.n_ctx,
                n_threads=self.config.n_threads,
                verbose=False,
            )
            self._status = "Ready (LLM)"
            return self._llm
        except (OSError, ValueError, RuntimeError):
            self._status = "Fallback (model load error)"
            return None

    @staticmethod
    def _fallback_hint(event_name: str, detail: str) -> str:
        if event_name == "face_locked":
            return "Face lock is stable; keep servo enabled and avoid changing PID gains."
        if event_name == "face_lost":
            return "Face lost; reduce pan speed and keep body tracking active for reacquisition."
        if event_name == "body_tracking":
            return "Body-only tracking active; keep timeout short and wait for frontal face return."
        if event_name == "tracking_lost":
            return "Tracking lost; reset servos to center and scan slowly before reattempt."
        if event_name == "coordinate_snapshot":
            return "Coordinates captured; prefer stabilized center and normalized values for control."
        return f"Event noted: {detail[:120]}"
