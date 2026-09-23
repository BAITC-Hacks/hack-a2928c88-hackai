"""Deterministic readiness score from case section 4, never from the LLM."""
from __future__ import annotations

from app.schemas import (
    CardContent, CardField, Confirmation, RatingBreakdown, RatingItem, TaskCard,
)

# Component splits are explicit implementation choices within official weights.
RUBRIC = (
    ("context_need", "Контекст и потребность", (("context", 10), ("need", 10))),
    ("data", "Данные и материалы", (("data", 20),)),
    ("result", "Ожидаемый результат", (("expected_result", 15),)),
    ("success", "Критерии успеха", (("success_criteria", 15),)),
    ("constraints", "Ограничения", (("constraints", 10),)),
    ("users", "Пользователи", (("users", 10),)),
    ("business", "Связь с бизнесом", (("contact", 4), ("interaction_format", 3), ("feedback_process", 3))),
)


def readiness_level(score: int) -> str:
    if type(score) is not int or not 0 <= score <= 100:
        raise ValueError("Score must be an integer from 0 to 100")
    if score < 40:
        return "draft"
    if score < 70:
        return "working"
    if score < 90:
        return "ready"
    return "priority"


def is_confirmed(card: TaskCard, field: str) -> bool:
    value = getattr(card, field)
    approval = card.confirmations.get(field)
    return bool(value.strip() and approval and approval.value == value)


def calculate_rating(card: TaskCard) -> RatingBreakdown:
    items = []
    missing_all = []
    for key, label, components in RUBRIC:
        confirmed = [field for field, _ in components if is_confirmed(card, field)]
        missing = [field for field, _ in components if field not in confirmed]
        earned = sum(points for field, points in components if field in confirmed)
        maximum = sum(points for _, points in components)
        missing_all.extend(missing)
        items.append(RatingItem(
            key=key, label=label, maximum=maximum, earned=earned,
            confirmed_fields=confirmed, missing_fields=missing,
            explanation=f"{earned}/{maximum}: " + "; ".join(
                f"{field} +{points if field in confirmed else 0} из {points}"
                for field, points in components
            ),
        ))
    total = sum(item.earned for item in items)
    return RatingBreakdown(
        total=total, level=readiness_level(total), items=items,
        missing_fields=missing_all, recommended_eligible=total >= 40,
    )


def confirm_fields(card: TaskCard, fields: list[CardField], *, business_actor: str) -> TaskCard:
    """Call only from the human confirmation action, never the AI handler.

    This foundation validates domain state; transport actor authorization belongs
    to the future API. A string actor is not authentication.
    """
    approvals = dict(card.confirmations)
    for field in fields:
        if field not in CardContent.model_fields:
            raise ValueError(f"Unknown card field: {field}")
        value = getattr(card, field)
        if not value.strip():
            raise ValueError(f"Cannot confirm empty field: {field}")
        approvals[field] = Confirmation(value=value, confirmed_by=business_actor)
    values = card.model_dump()
    values["confirmations"] = approvals
    return TaskCard.model_validate(values)


def edit_card(card: TaskCard, changes: dict[CardField, str]) -> TaskCard:
    values = card.model_dump()
    for field, value in changes.items():
        if field not in CardContent.model_fields:
            raise ValueError(f"Unknown card field: {field}")
        if value != values[field]:
            values["confirmations"].pop(field, None)
        values[field] = value
    return TaskCard.model_validate(values)
