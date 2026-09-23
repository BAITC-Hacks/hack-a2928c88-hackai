"""Conditional per-field improvements against the current published catalogue."""
from datetime import datetime, timezone
from app.rating import RUBRIC

LABELS = dict((field, label) for _, label, parts in RUBRIC for field, _ in parts)


def rank_key(card, score=None):
    return (-(card['rating']['total'] if score is None else score),
            card.get('first_published_at', ''), card['id'])


def catalog_insights(card, all_cards):
    others = [c for c in all_cards if c['id'] != card['id']]
    def position(score):
        key = rank_key(card, score)
        return 1 + sum(rank_key(c) < key for c in others)
    actions = []
    gains = [(field, points) for _, _, parts in RUBRIC for field, points in parts
             if field in card['rating']['missing_fields']]
    for field, points in sorted(gains, key=lambda item: -item[1])[:3]:
        filled = bool(card.get(field, '').strip())
        score_after = card['rating']['total'] + points
        actions.append(dict(field=field, label=LABELS[field],
            instruction='Проверьте и подтвердите поле' if filled else 'Заполните поле и подтвердите его',
            delta=points, score_after=score_after, rank_after=position(score_after)))
    return dict(revision=card['revision'], as_of=datetime.now(timezone.utc).isoformat(),
                rank=position(card['rating']['total']), total=len(all_cards), actions=actions,
                review=card.get('review', dict(status='not_run', revision=card['revision'],
                                             mode=None, provider=None, issues=[])))
