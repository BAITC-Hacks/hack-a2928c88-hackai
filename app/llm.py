"""Тонкая обёртка над OpenAI Responses API.

- Structured Outputs через Pydantic (`responses.parse`).
- Повтор при сбое, журнал вызовов в logs/llm_calls.jsonl (для демо и честной метрики).
- MOCK-режим: без ключа или при MOCK=1 возвращает детерминированный ответ,
  чтобы UI, тесты и деплой работали даже при проблемах с сетью на площадке.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

LOG_PATH = Path(os.getenv("LLM_LOG", "logs/llm_calls.jsonl"))
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
MODEL_STRONG = os.getenv("OPENAI_MODEL_STRONG", "gpt-5.5")


def is_mock() -> bool:
    return os.getenv("MOCK", "0") == "1" or not os.getenv("OPENAI_API_KEY")


def _log(entry: dict) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass  # журнал не должен ломать запрос


def parse(
    schema: type[T],
    instructions: str,
    user_input: str,
    *,
    strong: bool = False,
    mock: Callable[[], T] | None = None,
    retries: int = 2,
) -> T:
    """Вернуть объект `schema`, заполненный моделью."""
    if is_mock():
        if mock is None:
            raise RuntimeError("MOCK-режим: передайте mock-фабрику или задайте OPENAI_API_KEY")
        result = mock()
        _log({"ts": time.time(), "mode": "mock", "schema": schema.__name__})
        return result

    from openai import OpenAI  # импорт здесь: MOCK работает без пакета/ключа

    client = OpenAI()
    model = MODEL_STRONG if strong else MODEL
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        t0 = time.time()
        try:
            resp = client.responses.parse(
                model=model,
                instructions=instructions,
                input=user_input,
                text_format=schema,
            )
            out = resp.output_parsed
            usage = getattr(resp, "usage", None)
            _log({
                "ts": t0, "mode": "live", "model": model, "schema": schema.__name__,
                "latency_s": round(time.time() - t0, 2),
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
            })
            if out is None:
                raise RuntimeError("Модель не вернула структурированный ответ (refusal?)")
            return out
        except Exception as e:  # noqa: BLE001 — показываем причину в журнале
            last_err = e
            _log({"ts": t0, "mode": "live", "model": model, "error": repr(e)[:500], "attempt": attempt})
            time.sleep(1.5 * (attempt + 1))
    if mock is not None and os.getenv("FALLBACK_TO_MOCK", "1") == "1":
        return mock()
    raise RuntimeError(f"LLM недоступна: {last_err}")
