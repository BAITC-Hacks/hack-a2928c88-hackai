"""Агентный конвейер: извлечь -> проверить кодом -> найти смысловые проблемы -> отдать человеку.

Шаблон под «проверяющий агент с доказательствами» — подходит к гипотезам всех 10 треков
(см. context/tracks). После получения кейса поменять PROMPT_* и схемы, логику не усложнять
до тех пор, пока основной сценарий не работает end-to-end и не задеплоен.
"""
from __future__ import annotations

import uuid

from pydantic import BaseModel

from . import llm
from .rules import run_rules
from .schemas import Evidence, Extraction, ExtractedItem, Finding, LLMFinding, RunRequest, RunResult, Severity

# TODO(kickoff): переписать под кейс трека. Язык ответа — язык пользователя (RU/KZ).
PROMPT_EXTRACT = """Ты — аккуратный аналитик. Извлеки из документа ключевые поля.
Для КАЖДОГО поля приведи дословную цитату из входа (evidence.quote) и локатор —
метку вида [page N] / [sheet S row R] / [row R] / [para N], если она есть во входе.
Не выдумывай: если поля нет — добавь его имя в `missing`. Уверенность 0..1 честная."""

PROMPT_REVIEW = """Ты — проверяющий эксперт. По документу и извлечённым полям найди смысловые проблемы:
противоречия, неоднозначности, несоответствия требованиям. Каждую проблему подкрепи дословной
цитатой. Не повторяй то, что уже найдено правилами. Если проблем нет — верни пустой список."""


class Review(BaseModel):
    findings: list[LLMFinding]


def _mock_extraction(req: RunRequest) -> Extraction:
    first = req.text.strip().splitlines()[0][:200] if req.text.strip() else ""
    return Extraction(
        summary="[MOCK] Демонстрационное извлечение без вызова модели.",
        items=[ExtractedItem(key="first_line", value=first,
                             evidence=Evidence(source=req.source_name, quote=first, locator="line 1"),
                             confidence=0.9)],
        missing=[],
    )


def _mock_review() -> Review:
    return Review(findings=[LLMFinding(
        title="[MOCK] Пример смыслового замечания", severity=Severity.info,
        explanation="Задайте OPENAI_API_KEY, чтобы получить реальный разбор.",
        evidence=[], suggestion="")])


def run(req: RunRequest) -> RunResult:
    trace: list[dict] = []
    run_id = uuid.uuid4().hex[:8]

    ex = llm.parse(Extraction, PROMPT_EXTRACT,
                   f"SOURCE: {req.source_name}\n---\n{req.text}",
                   mock=lambda: _mock_extraction(req))
    trace.append({"step": "extract", "items": len(ex.items), "missing": ex.missing})

    rule_findings = run_rules(ex, req.text)
    trace.append({"step": "rules", "findings": len(rule_findings)})

    review = llm.parse(Review, PROMPT_REVIEW,
                       f"DOCUMENT:\n{req.text}\n\nEXTRACTED:\n{ex.model_dump_json()}\n\n"
                       f"RULE_FINDINGS:\n{[f.title for f in rule_findings]}",
                       strong=True, mock=_mock_review)
    llm_findings = []
    for n, f in enumerate(review.findings):
        llm_findings.append(Finding(id=f"LLM-{n + 1}", produced_by="llm", **f.model_dump()))
    trace.append({"step": "review", "findings": len(llm_findings)})

    return RunResult(run_id=run_id, extraction=ex, findings=rule_findings + llm_findings,
                     trace=trace, mode="mock" if llm.is_mock() else "live")
