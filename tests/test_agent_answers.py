from scripts.agents import extract_answer


def test_quoted_markers_after_answer_cannot_replace_actual_vote():
    raw = '<<<ANSWER\nAGREE\nConcrete reason.\nANSWER>>>\nMarkers are `<<<ANSWER` / `ANSWER>>>`.'
    assert extract_answer(raw) == 'AGREE\nConcrete reason.'


def test_last_real_delimited_answer_wins():
    raw = '<<<ANSWER\nEarlier\nANSWER>>>\n<<<ANSWER\nFinal\nANSWER>>>\n'
    assert extract_answer(raw) == 'Final'
