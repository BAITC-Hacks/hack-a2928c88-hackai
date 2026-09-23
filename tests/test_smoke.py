import os

os.environ["MOCK"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["ok"]


def test_index():
    assert client.get("/").status_code == 200


def test_run_decide_report():
    r = client.post("/api/run", json={"text": "Первая строка\nвторая"})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["mode"] == "mock" and res["findings"]
    fid = res["findings"][0]["id"]
    d = client.post(f"/api/runs/{res['run_id']}/decision", json={"finding_id": fid, "status": "accepted"})
    assert d.json()["findings"][0]["status"] == "accepted"
    assert "Отчёт" in client.get(f"/api/runs/{res['run_id']}/report").text


def test_quote_rule_catches_hallucination():
    from app.rules import quote_grounded
    from app.schemas import Evidence, ExtractedItem, Extraction
    ex = Extraction(summary="", items=[ExtractedItem(key="k", value="v", confidence=1,
                    evidence=Evidence(source="s", quote="этого нет в тексте", locator=""))], missing=[])
    assert quote_grounded(ex, "совсем другой текст")
