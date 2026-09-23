"""Pydantic-схемы. Адаптировать под кейс трека: переименовать поля, но сохранить
принцип «каждое утверждение имеет evidence (источник + фрагмент)»."""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Severity(str, Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class Evidence(BaseModel):
    source: str = Field(description="Имя документа/файла/строки, откуда взят факт")
    quote: str = Field(description="Дословный фрагмент источника (до 300 символов)")
    locator: str = Field(description="Страница, строка, ячейка или смещение; пусто, если нет")


class ExtractedItem(BaseModel):
    """То, что модель извлекает из входа. Переопределить под домен."""
    key: str = Field(description="Имя поля/сущности")
    value: str
    evidence: Evidence
    confidence: float = Field(ge=0, le=1)


class Extraction(BaseModel):
    summary: str
    items: list[ExtractedItem]
    missing: list[str] = Field(description="Что не найдено во входе")


class LLMFinding(BaseModel):
    """Схема для модели: без значений по умолчанию (strict Structured Outputs)."""
    title: str
    severity: Severity
    explanation: str
    evidence: list[Evidence]
    suggestion: str


class Finding(BaseModel):
    id: str
    title: str
    severity: Severity
    explanation: str
    evidence: list[Evidence]
    produced_by: Literal["rule", "llm"]
    rule_id: str = ""
    suggestion: str = ""
    status: Literal["pending", "accepted", "rejected"] = "pending"


class RunRequest(BaseModel):
    text: str = Field(min_length=1, max_length=200_000)
    source_name: str = "input"
    options: dict = Field(default_factory=dict)


class RunResult(BaseModel):
    run_id: str
    extraction: Extraction
    findings: list[Finding]
    trace: list[dict] = Field(default_factory=list, description="Шаги агента для демо/аудита")
    mode: Literal["live", "mock"]


class Decision(BaseModel):
    finding_id: str
    status: Literal["accepted", "rejected"]
    comment: str = ""
