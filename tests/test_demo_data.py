import json
from pathlib import Path

from app.rating import calculate_rating
from app.schemas import Draft, Proposal, TaskCard, TeamProfile


def test_synthetic_minimums_links_and_recomputed_readiness():
    raw = json.loads((Path(__file__).parents[1]/'data/samples/ai-sana-synthetic.json').read_text(encoding='utf-8'))
    assert raw['synthetic'] is True
    for key, schema in [('drafts',Draft),('cards',TaskCard),('teams',TeamProfile),('proposals',Proposal)]:
        assert len(raw[key]) >= 5
        for row in raw[key]:
            assert schema.model_validate(row).synthetic
    scores = []
    for row in raw['cards']:
        card = TaskCard.model_validate(row)
        score = calculate_rating(card).total
        assert score == raw['ratings'][card.id]['total']
        scores.append(score)
    assert min(scores) < 40 and max(scores) >= 90
    cards = {r['id'] for r in raw['cards']}
    teams = {r['id'] for r in raw['teams']}
    drafts = {r['id'] for r in raw['drafts']}
    assert all(c['draft_id'] in drafts for c in raw['cards'])
    assert all(p['task_id'] in cards and p['team_id'] in teams for p in raw['proposals'])
