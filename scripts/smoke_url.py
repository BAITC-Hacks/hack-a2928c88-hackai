"""Read-only deployed API smoke; does not claim UI or real AI acceptance."""
import argparse
import json
from urllib.request import urlopen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    if not base.startswith(("http://", "https://")):
        parser.error("Expected an HTTP(S) URL")
    def get(path):
        with urlopen(base + path, timeout=60) as response:
            return response.read().decode("utf-8")
    health = json.loads(get("/health"))
    assert health["status"] == "ok", health
    cards = json.loads(get("/api/cards"))
    teams = json.loads(get("/api/teams"))
    assert len(cards) >= 5 and len(teams) >= 5, "Expected seeded demo data"
    scores = [c["rating"]["total"] for c in cards]
    assert scores == sorted(scores, reverse=True), "Catalogue order"
    assert any(c["rating"]["total"] < 40 for c in cards), "Low-score case missing"
    assert "Sana" in get("/")
    assert "createDraft" in get("/static/api.js")
    print(json.dumps({"api_smoke": "passed", "cards": len(cards), "teams": len(teams),
                      "configured_mode": health["configured_mode"],
                      "ui_and_real_ai_verified": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
