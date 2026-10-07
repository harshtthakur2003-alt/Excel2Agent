"""Thin wrapper around the OpenAI SDK.

* ``available`` is False when no ``OPENAI_API_KEY`` is set (or ``AGENT_OFFLINE=1``).
  The agent then uses deterministic fallbacks so the whole project stays runnable
  and testable without network access or cost.
* All LLM traffic goes through two methods: ``tool_call`` (workflow routing) and
  ``json`` (structured generation / classification). This keeps prompts and
  provider details out of the workflows themselves.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Optional


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, model: Optional[str] = None, client: Any = None, offline: Optional[bool] = None):
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
        self.calls = 0
        if offline is None:
            offline = os.getenv("AGENT_OFFLINE", "0") == "1"
        self._client = client
        if self._client is None and not offline and os.getenv("OPENAI_API_KEY"):
            from openai import OpenAI
            self._client = OpenAI(timeout=float(os.getenv("OPENAI_TIMEOUT", "60")), max_retries=2)
        if offline and client is None:
            self._client = None

    # ------------------------------------------------------------------ #
    @property
    def available(self) -> bool:
        return self._client is not None

    @property
    def mode(self) -> str:
        return f"openai:{self.model}" if self.available else "offline-fallback"

    # ------------------------------------------------------------------ #
    def tool_call(self, system: str, user: str, tools: list[dict]) -> tuple[str, dict]:
        """Force the model to call exactly one of ``tools``; return (name, arguments)."""
        if not self.available:
            raise LLMError("LLM not available")
        resp = self._create(
            temperature=0,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            tools=tools,
            tool_choice="required",
        )
        msg = resp.choices[0].message
        if not getattr(msg, "tool_calls", None):
            raise LLMError("Model did not call a tool")
        call = msg.tool_calls[0]
        try:
            args = json.loads(call.function.arguments or "{}")
        except json.JSONDecodeError as exc:
            raise LLMError(f"Bad tool arguments: {exc}") from exc
        return call.function.name, args

    def json(self, system: str, user: str) -> dict:
        """Return a JSON object produced by the model (JSON mode)."""
        if not self.available:
            raise LLMError("LLM not available")
        resp = self._create(
            temperature=self.temperature,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system + "\nRespond with a single JSON object only."},
                      {"role": "user", "content": user}],
        )
        content = resp.choices[0].message.content or "{}"
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"Model returned invalid JSON: {exc}") from exc

    def _create(self, attempts: int = 2, **kwargs):
        """chat.completions.create with retry; drops `temperature` for models that reject it."""
        last: Exception | None = None
        for i in range(attempts):
            try:
                self.calls += 1
                return self._client.chat.completions.create(model=self.model, **kwargs)
            except Exception as exc:  # network / rate-limit / server errors
                last = exc
                if "temperature" in str(exc) and "temperature" in kwargs:
                    kwargs.pop("temperature")
                    continue
                time.sleep(0.5 * (i + 1))
        raise LLMError(f"OpenAI call failed: {last}")
