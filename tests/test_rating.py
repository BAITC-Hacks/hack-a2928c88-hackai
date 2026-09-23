import pytest
from pydantic import ValidationError

from app.rating import calculate_rating, confirm_fields, edit_card, readiness_level
from app.schemas import AISuggestion, CardContent, Decision, Draft, TaskCard, TeamProfile, Proposal


def full_card():
    return TaskCard(draft_id="draft-1", industry="retail", synthetic=True,
                    **{field: f"Business supplied {field}" for field in CardContent.model_fields})


def test_filled_ai_card_earns_nothing_without_human_confirmation():
    rating = calculate_rating(full_card())
    assert rating.total == 0
    assert rating.level == "draft"
    assert len(rating.missing_fields) == 10
    assert not rating.recommended_eligible


def test_full_confirmed_card_exact_official_weights_and_total():
    card = confirm_fields(full_card(), list(CardContent.model_fields), business_actor="business-1")
    rating = calculate_rating(card)
    assert [x.maximum for x in rating.items] == [20, 20, 15, 15, 10, 10, 10]
    assert [x.earned for x in rating.items] == [20, 20, 15, 15, 10, 10, 10]
    assert rating.total == 100 and rating.level == "priority"
    assert rating.missing_fields == []


def test_partial_score_explains_only_confirmed_components():
    card = confirm_fields(full_card(), ["context", "data", "contact"], business_actor="business-1")
    rating = calculate_rating(card)
    assert rating.total == 34
    assert rating.items[0].earned == 10
    assert rating.items[0].missing_fields == ["need"]
    assert rating.items[-1].earned == 4
    assert "feedback_process" in rating.missing_fields


def test_edit_revokes_score_until_reconfirmation_and_preserves_original():
    original = confirm_fields(full_card(), ["data"], business_actor="business-1")
    changed = edit_card(original, {"data": "New, unconfirmed material"})
    assert calculate_rating(original).total == 20
    assert calculate_rating(changed).total == 0
    assert calculate_rating(confirm_fields(changed, ["data"], business_actor="business-1")).total == 20


def test_direct_value_change_cannot_reuse_old_approval():
    card = confirm_fields(full_card(), ["data"], business_actor="business-1")
    card.data = "Different value"
    assert calculate_rating(card).total == 0


def test_longer_text_does_not_inflate_score_or_change_original():
    card = full_card()
    card.data = "Repeated content. " * 100
    card = confirm_fields(card, ["data"], business_actor="business-1")
    assert calculate_rating(card).total == 20
    same = edit_card(card, {"data": card.data})
    assert calculate_rating(same).total == 20


@pytest.mark.parametrize("score,level", [(0,"draft"),(39,"draft"),(40,"working"),(69,"working"),
                                         (70,"ready"),(89,"ready"),(90,"priority"),(100,"priority")])
def test_level_boundaries(score, level):
    assert readiness_level(score) == level


@pytest.mark.parametrize("score", [-1,101,40.5,True])
def test_invalid_scores(score):
    with pytest.raises(ValueError): readiness_level(score)


def test_empty_unknown_and_unauthorized_confirmation_data_rejected():
    card = full_card()
    card.data = "   "
    with pytest.raises(ValueError): confirm_fields(card, ["data"], business_actor="business-1")
    with pytest.raises(ValueError): confirm_fields(card, ["bogus"], business_actor="business-1")
    with pytest.raises(ValueError): confirm_fields(card, ["context"], business_actor=" ")
    with pytest.raises(ValueError): edit_card(card, {"confirmations": {}})


def test_title_is_not_an_extra_rating_category():
    assert calculate_rating(confirm_fields(full_card(), ["title"], business_actor="business-1")).total == 0


def test_ai_payload_cannot_confirm_fields_and_needs_three_distinct_questions():
    questions = [{"field":"data","question":f"Question {i}?"} for i in range(3)]
    payload = dict(content={}, evidence=[], questions=questions)
    AISuggestion.model_validate(payload)
    with pytest.raises(ValidationError): AISuggestion.model_validate({**payload,"confirmations":{}})
    with pytest.raises(ValidationError): AISuggestion.model_validate({**payload,"questions":questions[:2]})
    with pytest.raises(ValidationError): AISuggestion.model_validate({**payload,"questions":[questions[0]]*3})


def test_decision_is_per_proposal_and_business_only():
    assert Decision(proposal_id="p1", action="select", decided_by="business-1").actor == "business"
    Decision(proposal_id="p2", action="select", decided_by="business-1")
    Decision(proposal_id="p3", action="reject", decided_by="business-1")
    with pytest.raises(ValidationError):
        Decision(proposal_id="p1", action="select", decided_by="model", actor="ai")


def test_contract_rejects_empty_draft_sensitive_profile_and_bad_link():
    with pytest.raises(ValidationError): Draft(text=" ", industry="retail")
    with pytest.raises(ValidationError):
        TeamProfile(name="Team", interests=["retail"], skills=["python"], technologies=["fastapi"], age=20)
    with pytest.raises(ValidationError):
        Proposal(task_id="t1", team_id="c1", idea="idea", plan="plan", timeline="week", prototype_url="javascript:alert(1)")
