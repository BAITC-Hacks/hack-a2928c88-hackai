import json
from pathlib import Path

from app.rating import calculate_rating
from app.schemas import Draft, Proposal, TaskCard, TeamProfile


def test_synthetic_minimums_links_and_recomputed_readiness():
    raw = json.loads((Path(__file__).parents[1]/'data/samples/ai-sana-synthetic.json').read_text(encoding='utf-8'))
    assert raw['synthetic'] is True
    for key, schema in [('drafts',Draft),('cards',TaskCard),('teams',TeamProfile),('proposals',Proposal)]:
        assert len(raw[key]) >= 5
        assert len({row['id'] for row in raw[key]}) == len(raw[key])
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


def test_bulk_has_400_tasks_and_covers_four_readiness_levels():
    raw = json.loads((Path(__file__).parents[1]/'data/samples/ai-sana-synthetic.json').read_text(encoding='utf-8'))
    bulk = [c for c in raw['cards'] if c['id'].startswith('BULK-')]
    assert len(bulk) == 400
    assert {calculate_rating(TaskCard.model_validate(c)).total for c in bulk} == {20, 50, 75, 100}
    assert len([p for p in raw['proposals'] if p['task_id'].startswith('BULK-')]) == 400


def test_seed_upgrade_preserves_existing_records_and_is_retry_safe(tmp_path):
    from app.main import seed
    from app.store import Store

    store = Store(tmp_path / 'upgrade.sqlite3')
    existing = [('card', 'T1', {'revision': 9, 'snapshot': {'edited': True}}),
                ('proposal', 'P1', {'status': 'selected', 'progress_points': 10}),
                ('draft', 'D1', {'text': 'user edit'}),
                ('team', 'TEAM1', {'name': 'user team'}),
                ('card', 'user-created', {'custom': True})]
    with store.transaction() as db:
        for kind, identifier, body in existing:
            Store.put(db, kind, identifier, body)
        Store.put(db, 'meta', 'seeded', {'done': True})
    seed(store)
    with store.transaction() as db:
        for kind, identifier, body in existing:
            assert Store.get(db, kind, identifier) == body
        assert Store.get(db, 'card', 'BULK-T0400') is not None
        before = db.execute('SELECT kind, id, body FROM records ORDER BY kind, id').fetchall()
    seed(store)
    with store.transaction() as db:
        assert db.execute('SELECT kind, id, body FROM records ORDER BY kind, id').fetchall() == before
