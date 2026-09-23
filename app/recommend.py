"""Deterministic task recommendations for a team: word overlap, no AI, no ranking of teams.

A recommendation never hides the catalog; it only suggests eligible tasks (rating >= 40).
"""
import re

WORD = re.compile(r"[\w+#]+", re.UNICODE)
STEM = 5  # crude Russian stemming: compare word prefixes


def _stems(text: str) -> set[str]:
    return {w[:STEM] for w in WORD.findall(text.casefold()) if len(w) >= 3}


def _card_text(card: dict) -> str:
    return " ".join(str(card.get(k, "")) for k in
                    ("industry", "title", "context", "need", "users", "data", "expected_result", "constraints"))


def match_terms(team: dict, card: dict) -> list[str]:
    """Team profile phrases that share at least one word stem with the card."""
    card_stems = _stems(_card_text(card))
    phrases = [*team.get("interests", []), *team.get("skills", []), *team.get("technologies", [])]
    return [p for p in dict.fromkeys(phrases) if _stems(p) & card_stems]


def recommend(team: dict, cards: list[dict], limit: int) -> list[dict]:
    scored = []
    for card in cards:
        if card["rating"]["total"] < 40:
            continue
        matched = match_terms(team, card)
        if matched:
            scored.append((len(matched), card["rating"]["total"], card, matched))
    scored.sort(key=lambda row: (-row[0], -row[1], row[2]["id"]))
    return [{**card, "matched": matched} for _, _, card, matched in scored[:limit]]
