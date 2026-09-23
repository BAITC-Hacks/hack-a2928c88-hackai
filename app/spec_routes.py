"""Business-only draft endpoints and public, immutable-at-publication PDF snapshot."""
from datetime import datetime, timezone
from fastapi import Depends, Header, HTTPException, Response
from app.schemas import CardContent, TaskCard
from app.rating import is_confirmed
from app.store import Store
from app.review import carry_review, review_view
from app.specification import SpecSettings, SpecReview, source_fields, source_hash, spec_state, reviewed_document
from app.spec_pdf import specification_pdf


def ensure_confirmed(record):
    card = TaskCard.model_validate(record["card"])
    if not card.title.strip() or not card.need.strip():
        raise HTTPException(422, "Для ТЗ заполните название и потребность")
    if any(getattr(card, field).strip() and not is_confirmed(card, field) for field in CardContent.model_fields):
        raise HTTPException(422, "Сохраните и подтвердите заполненные поля карточки перед подготовкой ТЗ")


def draft_view(record):
    spec = record.get("specification", {})
    return {"id": record["card"]["id"], "revision": record["revision"], **spec_state(record),
            "content": spec.get("content"), "source": spec.get("source"),
            "selected_idea_ids": spec.get("selected_idea_ids", []),
            "mode": spec.get("mode"), "provider": spec.get("provider"),
            "warnings": spec.get("warnings", []), "review": review_view(record),
            "approved_at": spec.get("approved_at")}


def install_spec_routes(app, store, generator, business, require, check_revision):
    def save(db, id, record):
        record["revision"] += 1
        carry_review(record, record["revision"] - 1)
        Store.put(db, "card", id, record)
        return draft_view(record)

    def ready(record):
        spec = record.get("specification", {})
        if not spec.get("enabled") or not spec.get("content"):
            raise HTTPException(422, "Сначала включите подготовку ТЗ и сформируйте черновик")
        if spec_state(record)["stale"]:
            raise HTTPException(409, "Исходные данные изменились. Загрузите карточку и сформируйте ТЗ заново")
        return spec

    @app.get("/api/cards/{id}/specification/draft", dependencies=[Depends(business)])
    def get_draft(id: str):
        with store.transaction() as db:
            return draft_view(require(db, "card", id))

    @app.patch("/api/cards/{id}/specification/settings", dependencies=[Depends(business)])
    def settings(id: str, body: SpecSettings, if_match: str | None = Header(default=None)):
        with store.transaction() as db:
            record = require(db, "card", id)
            check_revision(record, if_match)
            spec = record.setdefault("specification", {})
            if spec.get("enabled", False) != body.enabled:
                spec.update(enabled=body.enabled, status="draft" if spec.get("content") else "empty", approved_at=None)
            return save(db, id, record)

    @app.post("/api/cards/{id}/specification/generate", dependencies=[Depends(business)])
    def generate(id: str, if_match: str | None = Header(default=None)):
        with store.transaction() as db:
            record = require(db, "card", id)
            check_revision(record, if_match)
            if not record.get("specification", {}).get("enabled"):
                raise HTTPException(422, "Включите переключатель «Составить ТЗ»")
            ensure_confirmed(record)
            source = source_fields(record)
        # Provider call runs outside the SQLite write transaction.
        try:
            content, mode, provider, warnings = generator.generate(source)
        except RuntimeError as exc:
            raise HTTPException(503, "AI недоступен. Попробуйте позже: черновик не изменён.") from exc
        with store.transaction() as db:
            current = require(db, "card", id)
            check_revision(current, if_match)  # Do not overwrite concurrent edits/toggle changes.
            current["specification"] = {"enabled": True, "status": "draft", "content": content.model_dump(),
                "selected_idea_ids": [], "source": source, "source_hash": source_hash(current),
                "mode": mode, "provider": provider, "warnings": warnings, "approved_at": None}
            return save(db, id, current)

    @app.put("/api/cards/{id}/specification/draft", dependencies=[Depends(business)])
    def edit_draft(id: str, body: SpecReview, if_match: str | None = Header(default=None)):
        with store.transaction() as db:
            record = require(db, "card", id)
            check_revision(record, if_match)
            spec = ready(record)
            spec.update(content=body.content.model_dump(), selected_idea_ids=body.selected_idea_ids,
                        status="draft", approved_at=None)
            return save(db, id, record)

    @app.post("/api/cards/{id}/specification/approve", dependencies=[Depends(business)])
    def approve(id: str, if_match: str | None = Header(default=None)):
        with store.transaction() as db:
            record = require(db, "card", id)
            check_revision(record, if_match)
            spec = ready(record)
            ensure_confirmed(record)
            spec.update(status="approved", approved_at=datetime.now(timezone.utc).isoformat())
            return save(db, id, record)

    def pdf_response(document, *, draft=False):
        try:
            data = specification_pdf(document, draft=draft)
        except RuntimeError as exc:
            raise HTTPException(503, "PDF временно недоступен: требуется шрифт с кириллицей") from exc
        return Response(data, media_type="application/pdf", headers={
            "Content-Disposition": 'attachment; filename="sana-specification.pdf"',
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

    @app.get("/api/cards/{id}/specification/draft.pdf", dependencies=[Depends(business)])
    def draft_pdf(id: str, if_match: str | None = Header(default=None)):
        with store.transaction() as db:
            record = require(db, "card", id)
            if if_match is not None:
                check_revision(record, if_match)
            spec = ready(record)
            document = reviewed_document(record)
        return pdf_response(document, draft=spec["status"] != "approved")

    def public_document(id):
        with store.transaction() as db:
            record = require(db, "card", id)
            document = (record.get("snapshot") or {}).get("technical_specification")
            if not document:
                raise HTTPException(404, "Утверждённое ТЗ ещё не опубликовано")
            return document

    @app.get("/api/cards/{id}/specification")
    def get_public(id: str):
        return public_document(id)

    @app.get("/api/cards/{id}/specification.pdf")
    def public_pdf(id: str):
        return pdf_response(public_document(id))
