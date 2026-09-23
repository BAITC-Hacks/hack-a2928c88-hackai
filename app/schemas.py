"""Domain contracts; AI suggestions have no authority to confirm or select."""
from __future__ import annotations

from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, field_validator, model_validator

NonEmpty = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
CardField = Literal[
    "title", "context", "need", "users", "data", "constraints",
    "expected_result", "success_criteria", "contact", "interaction_format",
    "feedback_process",
]
Readiness = Literal["draft", "working", "ready", "priority"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Draft(Model):
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: NonEmpty = Field(max_length=20000)
    industry: NonEmpty
    answers: dict[str, str] = Field(default_factory=dict)
    synthetic: bool = False


class CardContent(Model):
    title: str = ""
    context: str = ""
    need: str = ""
    users: str = ""
    data: str = ""
    constraints: str = ""
    expected_result: str = ""
    success_criteria: str = ""
    contact: str = ""
    interaction_format: str = ""
    feedback_process: str = ""


class Confirmation(Model):
    """Exact value approved by a human; editing invalidates that approval."""
    value: str = Field(min_length=1)
    confirmed_by: NonEmpty

    @field_validator("value")
    @classmethod
    def nonblank_exact_value(cls, value):
        if not value.strip():
            raise ValueError("Cannot confirm a blank value")
        return value


class TaskCard(CardContent):
    id: str = Field(default_factory=lambda: str(uuid4()))
    draft_id: NonEmpty
    industry: NonEmpty
    confirmations: dict[CardField, Confirmation] = Field(default_factory=dict)
    synthetic: bool = False


class RatingItem(Model):
    key: str
    label: str
    maximum: int = Field(ge=0, le=20)
    earned: int = Field(ge=0, le=20)
    confirmed_fields: list[CardField]
    missing_fields: list[CardField]
    explanation: str


class RatingGain(Model):
    """Points a missing field adds once a human confirms it."""
    field: CardField
    points: int = Field(ge=1, le=20)


class RatingBreakdown(Model):
    total: int = Field(ge=0, le=100)
    level: Readiness
    items: list[RatingItem]
    missing_fields: list[CardField]
    recommended_eligible: bool
    gains: list[RatingGain] = Field(default_factory=list)
    next_level: Readiness | None = None
    points_to_next: int = Field(default=0, ge=0, le=100)


class TeamProfile(Model):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: NonEmpty
    interests: list[NonEmpty] = Field(min_length=1)
    skills: list[NonEmpty] = Field(min_length=1)
    technologies: list[NonEmpty] = Field(min_length=1)
    synthetic: bool = False


class Proposal(Model):
    id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: NonEmpty
    team_id: NonEmpty
    idea: NonEmpty
    plan: NonEmpty
    timeline: NonEmpty
    prototype_url: HttpUrl
    synthetic: bool = False


class Decision(Model):
    """One decision per proposal allows zero, one or multiple chosen teams."""
    proposal_id: NonEmpty
    action: Literal["select", "reject"]
    decided_by: NonEmpty
    actor: Literal["business"] = "business"
    comment: str = ""


class FieldEvidence(Model):
    field: CardField
    source_id: NonEmpty
    quote: NonEmpty


class Clarification(Model):
    field: CardField
    question: NonEmpty


class AISuggestion(Model):
    """Separate from TaskCard: confirmation and decision fields are forbidden."""
    content: CardContent
    evidence: list[FieldEvidence]
    questions: list[Clarification] = Field(min_length=3)

    @model_validator(mode="after")
    def distinct_questions(self):
        if len({q.question.strip().casefold() for q in self.questions}) < 3:
            raise ValueError("At least three distinct clarification questions are required")
        return self
