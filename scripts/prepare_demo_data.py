"""Normalize Claude's explicitly synthetic fixtures, recomputing all scores."""
import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.schemas import CardContent, Draft, Proposal, TaskCard, TeamProfile
from app.rating import calculate_rating, confirm_fields

source = ROOT / 'coord/notes/Q-132813-claude.md'
blocks = re.findall(r'```json\s*(.*?)```', source.read_text(encoding='utf-8'), re.S)
draft_rows, card_rows, team_rows, proposal_rows = [json.loads(x) for x in blocks]
# Second hand-written synthetic source widens the catalog beyond the case minimum.
extra_source = ROOT / 'data/samples/synthetic-extra-source.json'
extra = json.loads(extra_source.read_text(encoding='utf-8'))
draft_rows += extra['drafts']
card_rows += extra['cards']
team_rows += extra['teams']
proposal_rows += extra['proposals']

from generate_synthetic_bulk import generate
bulk = generate([row['id'] for row in team_rows])
draft_rows += bulk['drafts']
card_rows += bulk['cards']
proposal_rows += bulk['proposals']
drafts = [Draft(**r, synthetic=True) for r in draft_rows]
draft_by_id = {d.id: d for d in drafts}
cards = []
ratings = {}
for row in card_rows:
    row = dict(row)
    claimed_score = row.pop('score')
    row.pop('level', None)
    row['industry'] = draft_by_id[row['draft_id']].industry
    card = TaskCard(**row, synthetic=True)
    fields = [f for f in CardContent.model_fields if getattr(card, f).strip()]
    # Fixture represents a labelled, manually supplied synthetic card, not an
    # AI output auto-approved in production. Runtime AI must never call this.
    card = confirm_fields(card, fields, business_actor='synthetic-fixture-author')
    rating = calculate_rating(card)
    assert rating.total == claimed_score, (card.id, rating.total, claimed_score)
    cards.append(card)
    ratings[card.id] = rating.model_dump()
teams = [TeamProfile(**r, synthetic=True) for r in team_rows]
proposals = [Proposal(id=f'P{i}', **r, synthetic=True) for i, r in enumerate(proposal_rows, 1)]
assert all(p.task_id in {c.id for c in cards} and p.team_id in {t.id for t in teams} for p in proposals)
payload = {
    'synthetic': True,
    'notice': 'Все организации, данные, профили, подтверждения и ссылки синтетические. Карточки — ручной эталон автора набора, не результат AI. example.com не является работающим прототипом.',
    'source': [source.relative_to(ROOT).as_posix(), extra_source.relative_to(ROOT).as_posix(), 'scripts/generate_synthetic_bulk.py'],
    'drafts': [d.model_dump(mode='json') for d in drafts],
    'cards': [c.model_dump(mode='json') for c in cards],
    'ratings': ratings,
    'teams': [t.model_dump(mode='json') for t in teams],
    'proposals': [p.model_dump(mode='json') for p in proposals],
}
folder = ROOT / 'data/samples'
folder.mkdir(parents=True, exist_ok=True)
(folder/'ai-sana-synthetic.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
print({key: len(payload[key]) for key in ['drafts', 'cards', 'teams', 'proposals']})
