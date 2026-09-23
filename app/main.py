"""Transactional demo API. Demo roles are controls, not authentication."""
import os
import json
import asyncio
import logging
from contextlib import suppress
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header, Depends, Query, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field, HttpUrl
from app.llm import Extractor
from app.rating import calculate_rating, confirm_fields, edit_card, is_confirmed
from app.recommend import recommend
from app.review import CardReviewer, review_view, carry_review
from app.insights import catalog_insights
from app.stages import register_stages
from app.schemas import Model, Draft, TaskCard, CardContent, CardField, Proposal, TeamProfile, NonEmpty
from app.store import Store
from app.specification import SpecGenerator, spec_state, reviewed_document
from app.spec_routes import install_spec_routes
from app.community import register_community, seed_community, deliver_notifications
from app.questions import register_questions
from app.question_suggestion import QuestionSuggester
from app.project_letters import register_project_letters

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent


class DraftInput(Model):
    text: NonEmpty = Field(max_length=20000)
    industry: NonEmpty = Field(max_length=120)
    synthetic: bool = False


class BuildInput(Model):
    answers: dict[str, str] = Field(default_factory=dict)


class EditInput(Model):
    changes: dict[CardField, str]


class ConfirmInput(Model):
    fields: list[CardField] = Field(min_length=1, max_length=11)


class ProposalInput(Model):
    team_id: NonEmpty
    idea: NonEmpty = Field(max_length=5000)
    plan: NonEmpty = Field(max_length=5000)
    timeline: NonEmpty = Field(max_length=1000)
    prototype_url: HttpUrl


class DecisionInput(Model):
    action: Literal["select", "reject"]


def business(x_demo_role: str = Header(default="")):
    if x_demo_role != "business":
        raise HTTPException(403, "Действие доступно только роли бизнеса в демо")


def student(x_demo_role: str = Header(default="")):
    if x_demo_role != "team":
        raise HTTPException(403, "Действие доступно только роли команды в демо")


def require(db, kind, id):
    record = Store.get(db, kind, id)
    if record is None:
        raise HTTPException(404, "Запись не найдена")
    return record


def check_revision(record, revision):
    if revision is None:
        raise HTTPException(428, "Нужен If-Match с revision карточки")
    if revision != str(record["revision"]):
        raise HTTPException(409, "Карточка изменилась. Обновите страницу перед действием")


def card_view(record):
    card = TaskCard.model_validate(record["card"])
    value = card.model_dump(mode="json", exclude={"confirmations"})
    value.update(confirmed_fields=[f for f in CardContent.model_fields if is_confirmed(card, f)],
        rating=calculate_rating(card).model_dump(), evidence=record["evidence"],
        mode=record["mode"], provider=record.get("provider", "mock"), warnings=record.get("warnings", []),
        review=review_view(record), specification=spec_state(record),
        revision=record["revision"], published=record.get("snapshot") is not None,
        has_unpublished_changes=bool(record.get("snapshot") and (
            record["snapshot"]["revision"] != record["revision"] or
            (record.get('review') and record['snapshot'].get('review') != review_view(record)))))
    return value


def seed(store):
    fixtures = json.loads((ROOT / "data/samples/ai-sana-synthetic.json").read_text(encoding="utf-8"))
    with store.transaction() as db:
        # Add missing fixture IDs on upgrades, preserving all existing records.
        # Same schema: previous app versions can still read this database.
        for draft in fixtures["drafts"]:
            item = Draft.model_validate(draft).model_dump(mode="json")
            if Store.get(db, "draft", item["id"]) is not None:
                continue
            Store.put(db, "draft", item["id"], {"draft": item, "questions": [], "card_id": None})
        for team in fixtures["teams"]:
            item = TeamProfile.model_validate(team).model_dump(mode="json")
            if Store.get(db, "team", item["id"]) is not None:
                continue
            Store.put(db, "team", item["id"], item)
        for card in fixtures["cards"]:
            item = TaskCard.model_validate(card).model_dump(mode="json")
            if Store.get(db, "card", item["id"]) is not None:
                continue
            record = {"card": item, "revision": 1, "mode": "mock", "provider": "synthetic-fixture",
                # Prepared synthetic cards are examples, not extracted source evidence.
                "evidence": {}, "snapshot": None}
            record["first_published_at"] = "2026-09-23T08:00:00+00:00"
            record["snapshot"] = card_view(record)
            record["snapshot"]["first_published_at"] = record["first_published_at"]
            record["snapshot"]["published"] = True
            Store.put(db, "card", item["id"], record)
        for proposal in fixtures["proposals"]:
            item = Proposal.model_validate(proposal).model_dump(mode="json")
            if Store.get(db, "proposal", item["id"]) is not None:
                continue
            item.update(status="pending", progress_points=0)
            Store.put(db, "proposal", item["id"], item)
        Store.put(db, "meta", "seeded", {"done": True})


def create_app(database_path=None, seed_demo=None, extractor=None, reviewer=None, spec_generator=None):
    store = Store(database_path or os.getenv("DATABASE_PATH", "data/runtime/sana.sqlite3"))
    ai = extractor or Extractor()
    critic = reviewer or CardReviewer(ai)
    spec_ai = spec_generator or SpecGenerator(ai.reserve if hasattr(ai, "reserve") else Extractor().reserve)

    @asynccontextmanager
    async def lifespan(app):
        should_seed = seed_demo if seed_demo is not None else os.getenv("SEED_DEMO", "1") == "1"
        if should_seed:
            seed(store)
        seed_community(store)
        async def notification_loop():
            while True:
                try:
                    await asyncio.to_thread(deliver_notifications, store)
                except Exception:
                    logging.getLogger(__name__).exception('Notification delivery failed; will retry')
                await asyncio.sleep(60)
        worker = asyncio.create_task(notification_loop())
        try:
            yield
        finally:
            worker.cancel()
            with suppress(asyncio.CancelledError):
                await worker

    app = FastAPI(title="Sana Hub", version="0.2.0", lifespan=lifespan)
    app.state.store = store
    install_spec_routes(app, store, spec_ai, business, require, check_revision)
    community = register_community(app, store, require)
    register_questions(app, store, require, **community,
                       suggest_field=QuestionSuggester(ai.reserve if hasattr(ai, 'reserve') else Extractor().reserve))
    register_project_letters(app, store, require, **community)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "sana-hub", "demo_auth": True,
            "configured_mode": "mock" if os.getenv("MOCK", "1") == "1" else "live-with-fallback"}

    @app.post("/api/drafts", dependencies=[Depends(business)], status_code=201)
    def create_draft(body: DraftInput):
        draft = Draft(**body.model_dump())
        with store.transaction() as db:
            Store.put(db, "draft", draft.id, {"draft": draft.model_dump(), "questions": [], "card_id": None})
        return {"id": draft.id}

    def extract(sources, fields):
        try:
            return ai.extract(sources, fields)
        except ValueError as exc:
            raise HTTPException(422, "Недопустимые данные или цитаты") from exc
        except RuntimeError as exc:
            raise HTTPException(503, "AI недоступен, резервный mock отключён") from exc

    @app.post("/api/drafts/{id}/clarify", dependencies=[Depends(business)])
    def clarify(id: str):
        with store.transaction() as db:
            record = require(db, "draft", id)
            if record["questions"]:
                return {"questions": record["questions"], "mode": record["mode"], "provider": record["provider"]}
        result, mode, provider, warnings = extract({"draft": record["draft"]["text"]}, {})
        questions = [{"id": f"q-{i}", **q.model_dump()} for i, q in enumerate(result.questions)]
        with store.transaction() as db:
            current = require(db, "draft", id)
            if not current["questions"]:
                current.update(questions=questions, mode=mode, provider=provider, warnings=warnings)
                Store.put(db, "draft", id, current)
            return {"questions": current["questions"], "mode": current["mode"], "provider": current["provider"]}

    @app.post("/api/drafts/{id}/card", dependencies=[Depends(business)])
    def build(id: str, body: BuildInput):
        with store.transaction() as db:
            record = require(db, "draft", id)
            if record["card_id"]:
                return card_view(require(db, "card", record["card_id"]))
        if not record["questions"]:
            raise HTTPException(409, "Сначала запросите уточняющие вопросы")
        fields = {q["id"]: q["field"] for q in record["questions"]}
        if body.answers.keys() - fields.keys() or sum(map(len, body.answers.values())) > 10000:
            raise HTTPException(422, "Неизвестный вопрос или слишком длинные ответы")
        result, mode, provider, warnings = extract({"draft": record["draft"]["text"], **body.answers}, fields)
        card = TaskCard(**{e.field: e.quote for e in result.evidence}, draft_id=id,
            industry=record["draft"]["industry"], synthetic=record["draft"]["synthetic"])
        new = {"card": card.model_dump(), "revision": 1, "mode": mode, "provider": provider, "warnings": warnings,
            "evidence": {e.field: {"source_id": e.source_id, "quote": e.quote} for e in result.evidence}, "snapshot": None}
        with store.transaction() as db:
            current = require(db, "draft", id)
            if current["card_id"]:
                return card_view(require(db, "card", current["card_id"]))
            current["card_id"] = card.id
            current["draft"]["answers"] = body.answers
            Store.put(db, "draft", id, current)
            Store.put(db, "card", card.id, new)
        return card_view(new)

    def published(db):
        counts = {}
        for p in Store.all(db, "proposal"):
            counts[p["task_id"]] = counts.get(p["task_id"], 0) + 1
        cards = [{**r["snapshot"], "proposals_count": counts.get(r["snapshot"]["id"], 0)}
                 for r in Store.all(db, "card") if r.get("snapshot")]
        return sorted(cards, key=lambda c: (-c["rating"]["total"], c.get("first_published_at", ""), c["id"]))

    def matches(card, q):
        text = " ".join(str(card.get(k, "")) for k in ("title", "industry", "context", "need", "data", "expected_result"))
        return q in text.casefold()

    @app.get("/api/cards")
    def list_cards(response: Response, industry: str = "", level: str = "",
                   q: str = Query(default="", max_length=200),
                   limit: int | None = Query(default=None, ge=1, le=100), offset: int = Query(default=0, ge=0)):
        # Without limit the full ranked list is returned, as before; the total is always in a header.
        with store.transaction() as db:
            cards = published(db)
        needle = q.strip().casefold()
        found = [c for c in cards if (not industry or c["industry"] == industry) and
                 (not level or c["rating"]["level"] == level) and (not needle or matches(c, needle))]
        response.headers["X-Total-Count"] = str(len(found))
        page = found[offset:offset + limit] if limit else found[offset:]
        return [{**c, 'catalog_insights': catalog_insights(c, cards)} for c in page]

    @app.get("/api/catalog/facets")
    def facets():
        with store.transaction() as db:
            cards = published(db)
        industries, levels = {}, {"draft": 0, "working": 0, "ready": 0, "priority": 0}
        for c in cards:
            industries[c["industry"]] = industries.get(c["industry"], 0) + 1
            levels[c["rating"]["level"]] += 1
        ranked = sorted(industries.items(), key=lambda item: (-item[1], item[0]))
        return {"total": len(cards), "industries": [{"name": n, "count": k} for n, k in ranked], "levels": levels}

    @app.get("/api/cards/{id}")
    def get_card(id: str):
        with store.transaction() as db:
            return card_view(require(db, "card", id))

    @app.post("/api/cards/{id}/review", dependencies=[Depends(business)])
    def review_card(id: str, if_match: str | None = Header(default=None)):
        with store.transaction() as db:
            record = require(db, "card", id)
            check_revision(record, if_match)
            fields = CardContent.model_validate({f: record['card'][f] for f in CardContent.model_fields}).model_dump()
        # No transaction is held while awaiting the provider. Recheck revision after it returns.
        try:
            result = critic.review(fields)
        except ValueError as exc:
            raise HTTPException(422, 'Недопустимая карточка для проверки') from exc
        except RuntimeError as exc:
            raise HTTPException(503, 'Проверка недоступна. Текст сохранён; попробуйте ещё раз.') from exc
        with store.transaction() as db:
            current = require(db, "card", id)
            check_revision(current, if_match)
            current['review'] = {**result, 'revision': current['revision']}
            Store.put(db, 'card', id, current)
            return card_view(current)

    def mutate(id, revision, operation):
        with store.transaction() as db:
            record = require(db, "card", id)
            check_revision(record, revision)
            card = TaskCard.model_validate(record["card"])
            try:
                operation(record, card)
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
            record["revision"] += 1
            if all(record['card'][f] == getattr(card, f) for f in CardContent.model_fields):
                carry_review(record, record['revision'] - 1)
            Store.put(db, "card", id, record)
            return card_view(record)

    @app.patch("/api/cards/{id}", dependencies=[Depends(business)])
    def update_card(id: str, body: EditInput, if_match: str | None = Header(default=None)):
        if sum(map(len, body.changes.values())) > 30000:
            raise HTTPException(422, "Слишком длинная карточка")
        def apply(record, card):
            updated = edit_card(card, body.changes)
            if sum(len(getattr(updated, f)) for f in CardContent.model_fields) > 30000:
                raise ValueError("Card exceeds 30000 characters")
            record["card"] = updated.model_dump()
            if any(getattr(card, f) != value for f, value in body.changes.items()):
                spec = record.get("specification", {})
                if spec.get("content"):
                    spec["status"] = "stale"
                    spec["approved_at"] = None
            for f, value in body.changes.items():
                if getattr(card, f) != value:
                    record["evidence"].pop(f, None)
                    if value.strip():
                        record["evidence"][f] = {"source_id": f"manual:{id}:{record['revision'] + 1}:{f}", "quote": value}
        return mutate(id, if_match, apply)

    @app.post("/api/cards/{id}/confirm", dependencies=[Depends(business)])
    def confirm(id: str, body: ConfirmInput, if_match: str | None = Header(default=None)):
        def apply(record, card):
            record["card"] = confirm_fields(card, body.fields, business_actor="demo-business").model_dump()
        return mutate(id, if_match, apply)

    @app.post("/api/cards/{id}/publish", dependencies=[Depends(business)])
    def publish(id: str, if_match: str | None = Header(default=None)):
        with store.transaction() as db:
            record = require(db, "card", id)
            check_revision(record, if_match)
            card = TaskCard.model_validate(record["card"])
            if not card.title.strip() or any(getattr(card, f).strip() and not is_confirmed(card, f) for f in CardContent.model_fields):
                raise HTTPException(422, "Укажите название и подтвердите каждое заполненное поле")
            specification = spec_state(record)
            if specification["enabled"] and specification["status"] != "approved":
                raise HTTPException(422, "Проверьте и утвердите актуальное ТЗ или выключите его подготовку")
            record["revision"] += 1
            carry_review(record, record['revision'] - 1)
            record.setdefault("first_published_at", datetime.now(timezone.utc).isoformat())
            record["snapshot"] = card_view(record)
            record["snapshot"].update(published=True, has_unpublished_changes=False, first_published_at=record["first_published_at"])
            record["snapshot"]["technical_specification"] = reviewed_document(record) if specification["enabled"] else None
            Store.put(db, "card", id, record)
            return {**card_view(record), 'catalog_insights': catalog_insights(record['snapshot'], published(db))}

    @app.get("/api/teams")
    def teams():
        with store.transaction() as db:
            return Store.all(db, "team")

    @app.get("/api/teams/{id}/recommendations")
    def recommendations(id: str, limit: int = Query(default=10, ge=1, le=50)):
        with store.transaction() as db:
            team = require(db, "team", id)
            cards = published(db)
        return [{**c, 'catalog_insights': catalog_insights(c, cards)} for c in recommend(team, cards, limit)]

    def proposal_view(db, item):
        return {**item, "team_name": require(db, "team", item["team_id"])["name"]}

    @app.post("/api/cards/{id}/proposals", dependencies=[Depends(student)], status_code=201)
    def create_proposal(id: str, body: ProposalInput):
        with store.transaction() as db:
            card = require(db, "card", id)
            if not card.get("snapshot"):
                raise HTTPException(409, "Карточка ещё не опубликована")
            team = require(db, "team", body.team_id)
            proposal = Proposal(task_id=id, **body.model_dump(), synthetic=card["snapshot"]["synthetic"] or team["synthetic"])
            item = proposal.model_dump(mode="json")
            key = json.dumps([id, body.team_id, "prototype"])
            item.update(status="pending", progress_points=10 if Store.get(db, "milestone", key) else 0,
                card_revision=card["snapshot"]["revision"], task_snapshot=card["snapshot"])
            Store.put(db, "proposal", proposal.id, item)
            return proposal_view(db, item)

    @app.get("/api/cards/{id}/proposals")
    def proposals(id: str):
        with store.transaction() as db:
            require(db, "card", id)
            return [proposal_view(db, p) for p in Store.all(db, "proposal") if p["task_id"] == id]

    @app.post("/api/proposals/{id}/decision", dependencies=[Depends(business)])
    def decide(id: str, body: DecisionInput):
        with store.transaction() as db:
            item = require(db, "proposal", id)
            item["status"] = "selected" if body.action == "select" else "rejected"
            item["decided_by"] = "demo-business"
            Store.put(db, "proposal", id, item)
            return proposal_view(db, item)

    @app.post("/api/proposals/{id}/milestone", dependencies=[Depends(business)])
    def milestone(id: str):
        with store.transaction() as db:
            item = require(db, "proposal", id)
            if item["status"] != "selected":
                raise HTTPException(409, "Сначала бизнес должен выбрать команду")
            key = json.dumps([item["task_id"], item["team_id"], "prototype"])
            stage = Store.get(db, 'stage', key)
            if stage:
                if stage['status'] != 'accepted':
                    raise HTTPException(409, 'Для этого этапа нужна приёмка результата на экране бизнеса')
                return {'points': 10, 'already_awarded': True}
            awarded = bool(Store.get(db, "milestone", key))
            Store.put(db, "milestone", key, {"points": 10, "confirmed_by": "demo-business"})
            for p in Store.all(db, "proposal"):
                if p["task_id"] == item["task_id"] and p["team_id"] == item["team_id"]:
                    p["progress_points"] = 10
                    Store.put(db, "proposal", p["id"], p)
            return {"points": 10, "already_awarded": awarded}

    register_stages(app, store, require, business, student)

    static = ROOT / "app/static"
    static.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=static), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(static / "index.html")

    return app


app = create_app()
