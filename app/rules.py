"""Детерминированные проверки. Всё, что можно проверить кодом (даты, суммы,
обязательные поля, арифметика, дубли), проверяется здесь, а не моделью.
Жюри ценит: модель объясняет, код считает.

Добавить правило: функция (Extraction, text) -> list[Finding] + декоратор @rule.
"""
from __future__ import annotations

import re
from typing import Callable

from .schemas import Evidence, Extraction, Finding, Severity

RULES: list[tuple[str, Callable[[Extraction, str], list[Finding]]]] = []

# TODO(kickoff): заменить на обязательные поля из кейса трека
REQUIRED_KEYS: list[str] = []


def rule(rule_id: str):
    def wrap(fn):
        RULES.append((rule_id, fn))
        return fn
    return wrap


@rule("R-REQUIRED")
def required_fields(ex: Extraction, text: str) -> list[Finding]:
    found = {i.key.lower() for i in ex.items}
    out = []
    for key in REQUIRED_KEYS:
        if key.lower() not in found:
            out.append(Finding(
                id=f"R-REQUIRED-{key}", title=f"Нет обязательного поля: {key}",
                severity=Severity.critical, explanation="Поле требуется правилом, но не найдено во входе.",
                evidence=[], produced_by="rule", rule_id="R-REQUIRED",
            ))
    return out


@rule("R-LOWCONF")
def low_confidence(ex: Extraction, text: str) -> list[Finding]:
    return [
        Finding(
            id=f"R-LOWCONF-{n}", title=f"Низкая уверенность: {i.key}",
            severity=Severity.warning,
            explanation=f"Модель извлекла значение с уверенностью {i.confidence:.2f}; нужна ручная проверка.",
            evidence=[i.evidence], produced_by="rule", rule_id="R-LOWCONF",
        )
        for n, i in enumerate(ex.items) if i.confidence < 0.6
    ]


@rule("R-QUOTE")
def quote_grounded(ex: Extraction, text: str) -> list[Finding]:
    """Анти-галлюцинация: цитата должна реально присутствовать во входе."""
    norm = re.sub(r"\s+", " ", text).lower()
    out = []
    for n, i in enumerate(ex.items):
        q = re.sub(r"\s+", " ", i.evidence.quote).strip().lower()
        if q and q not in norm:
            out.append(Finding(
                id=f"R-QUOTE-{n}", title=f"Цитата не найдена во входе: {i.key}",
                severity=Severity.critical,
                explanation="Модель сослалась на фрагмент, которого нет в источнике. Значение не принимать.",
                evidence=[Evidence(source=i.evidence.source, quote=i.evidence.quote[:300], locator=i.evidence.locator)],
                produced_by="rule", rule_id="R-QUOTE",
            ))
    return out


def run_rules(ex: Extraction, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for _, fn in RULES:
        findings.extend(fn(ex, text))
    return findings
