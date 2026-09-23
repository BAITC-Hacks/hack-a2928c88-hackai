"""API additions used by the redesigned UI: gains, paging, facets, recommendations."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.rating import calculate_rating, confirm_fields
from app.schemas import CardContent, TaskCard

T = {"X-Demo-Role": "team"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK", "1")
    with TestClient(create_app(tmp_path / "ui.db", seed_demo=True)) as client:
        yield client


def card_with(*confirmed):
    card = TaskCard(draft_id="d", industry="retail",
                    **{f: f"value {f}" for f in CardContent.model_fields})
    return confirm_fields(card, list(confirmed), business_actor="b") if confirmed else card


def test_gains_list_missing_fields_by_points_descending():
    rating = calculate_rating(card_with("context", "need", "users", "contact"))
    assert rating.total == 34
    assert [(g.field, g.points) for g in rating.gains] == [
        ("data", 20), ("expected_result", 15), ("success_criteria", 15),
        ("constraints", 10), ("interaction_format", 3), ("feedback_process", 3)]
    assert sum(g.points for g in rating.gains) == 100 - rating.total


def test_next_level_distance_uses_case_thresholds():
    working = calculate_rating(card_with("context", "need", "users", "contact", "interaction_format", "feedback_process"))
    assert working.total == 40 and working.next_level == "ready" and working.points_to_next == 30
    priority = calculate_rating(card_with(*CardContent.model_fields))
    assert priority.next_level is None and priority.points_to_next == 0 and priority.gains == []


def test_catalog_paging_keeps_order_and_reports_total(client):
    everything = client.get("/api/cards").json()
    page = client.get("/api/cards?limit=5&offset=5")
    assert page.status_code == 200
    assert int(page.headers["X-Total-Count"]) == len(everything)
    assert [c["id"] for c in page.json()] == [c["id"] for c in everything[5:10]]
    assert all("proposals_count" in c for c in page.json())


def test_catalog_search_matches_title_and_text_case_insensitive(client):
    found = client.get("/api/cards?q=КОНВЕЙЕР").json()
    assert found and all("конвейер" in (c["title"] + c["need"] + c["context"]).lower() for c in found)
    assert client.get("/api/cards?q=zzzz-nothing").json() == []


def test_catalog_rejects_invalid_paging(client):
    assert client.get("/api/cards?limit=0").status_code == 422
    assert client.get("/api/cards?limit=101").status_code == 422
    assert client.get("/api/cards?offset=-1").status_code == 422


def test_facets_count_published_cards_by_industry_and_level(client):
    facets = client.get("/api/catalog/facets").json()
    cards = client.get("/api/cards").json()
    assert facets["total"] == len(cards)
    assert sum(i["count"] for i in facets["industries"]) == len(cards)
    assert sum(facets["levels"].values()) == len(cards)
    counts = [i["count"] for i in facets["industries"]]
    assert counts == sorted(counts, reverse=True)


def test_recommendations_only_eligible_cards_with_reasons(client):
    teams = {t["name"]: t["id"] for t in client.get("/api/teams").json()}
    recs = client.get(f"/api/teams/{teams['LedgerLab']}/recommendations?limit=5").json()
    assert recs and len(recs) <= 5
    assert all(r["rating"]["total"] >= 40 and r["matched"] for r in recs)
    assert recs[0]["id"] == "T9"


def test_recommendations_unknown_team_is_404(client):
    assert client.get("/api/teams/nope/recommendations").status_code == 404


def test_proposal_counts_follow_new_proposals(client):
    card = client.get("/api/cards?q=Анализ отзывов гостей").json()[0]
    before = card["proposals_count"]
    team = client.get("/api/teams").json()[0]
    client.post(f"/api/cards/{card['id']}/proposals", headers=T, json={
        "team_id": team["id"], "idea": "i", "plan": "p", "timeline": "1 нед",
        "prototype_url": "https://example.com/x"})
    after = client.get("/api/cards?q=Анализ отзывов гостей").json()[0]["proposals_count"]
    assert after == before + 1
