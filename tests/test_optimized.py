"""Correctness, per-ticket budgets, edge cases, and local audit checks."""
import json
from dataclasses import asdict

import pytest

import question1.agent as q1
import question2.agent as q2
from shared.kb import article_ids
from shared.tools import get_order, get_ticket

EXPECTED = [
    ("T-1001", "REFUND", "returns-within-30-days"),
    ("T-1002", "SEND_ARTICLE", "digital-license-no-refund"),
    ("T-1003", "ESCALATE_TIER2", "custom-items-no-replace"),
    ("T-1004", "REPLACE", "damage-replacement-7-days"),
    ("T-1091", "SEND_ARTICLE", "subscription-cooling-off"),
]
AGENTS = [(q1, q1.SupportCopilot, 3000), (q2, q2.SupportPipeline, 2500)]


@pytest.mark.parametrize("module,agent_class,budget", AGENTS)
@pytest.mark.parametrize("ticket_id,action,article", EXPECTED)
def test_correctness_and_individual_budget(module, agent_class, budget, ticket_id, action, article):
    agent = agent_class()
    result = agent.handle_ticket(ticket_id)
    assert (result.action, result.kb_article) == (action, article)
    assert len(agent.session.calls) == 1
    assert 0 < agent.session.total_points() <= budget
    call = agent.session.calls[0]
    assert call.cached_prefix_tokens == 0
    # Compact formatting must not drop a field or alter a bool/int.
    snapshot = call.prompt.split("ORDER_SNAPSHOT:\n", 1)[1].split("\nEND_SNAPSHOT", 1)[0]
    assert json.loads(snapshot) == get_order(get_ticket(ticket_id)["order_id"])


@pytest.mark.parametrize("module,agent_class,budget", AGENTS)
@pytest.mark.parametrize("updates,action,article", [
    ({"delivered_days_ago": 30}, "REFUND", "returns-within-30-days"),
    ({"delivered_days_ago": 31}, "ESCALATE_TIER2", "returns-within-30-days"),
    ({"opened": True}, "ESCALATE_TIER2", "returns-within-30-days"),
    ({"damage_reported": True, "opened": True, "delivered_days_ago": 7}, "REPLACE", "damage-replacement-7-days"),
    ({"damage_reported": True, "opened": True, "delivered_days_ago": 8}, "ESCALATE_TIER2", "returns-within-30-days"),
    ({"damage_reported": True, "customized": True}, "ESCALATE_TIER2", "custom-items-no-replace"),
    ({"license_revealed": True}, "SEND_ARTICLE", "digital-license-no-refund"),
    ({"product_type": "subscription", "subscription_age_days": 30}, "REFUND", "subscription-cooling-off"),
    ({"product_type": "subscription", "subscription_age_days": 31}, "SEND_ARTICLE", "subscription-cooling-off"),
    ({"product_type": "unknown"}, "ESCALATE_TIER2", "returns-within-30-days"),
])
def test_new_order_facts_not_ticket_id_lookup(monkeypatch, module, agent_class, budget, updates, action, article):
    order = get_order("ord_4421")
    order.update(updates)
    monkeypatch.setattr(module, "get_ticket", lambda tid: {
        "order_id": "unseen-order",
        "messages": [{"from": "customer", "text": "Please resolve my request."}],
    })
    monkeypatch.setattr(module, "get_order", lambda oid: order)
    result = agent_class().handle_ticket("UNSEEN-TICKET")
    assert (result.action, result.kb_article) == (action, article)


def test_unknown_category_retrieves_all_real_policies():
    pipe = q2.SupportPipeline()
    triage = pipe._triage({"product_type": "unknown"})
    assert set(pipe._retrieve(triage)) == set(article_ids())


@pytest.mark.parametrize("draft", [
    "not json",
    "[]",
    '{"action": "DELETE", "kb_article": "returns-within-30-days", "customer_reply": "Hi"}',
    '{"action": [], "kb_article": "returns-within-30-days", "customer_reply": "Hi"}',
    '{"action": "REFUND", "kb_article": "invented-policy", "customer_reply": "Hi"}',
    '{"action": "REFUND", "kb_article": [], "customer_reply": "Hi"}',
    '{"action": "REFUND", "kb_article": "returns-within-30-days", "customer_reply": ""}',
])
def test_audit_rejects_bad_output(draft):
    pipe = q2.SupportPipeline()
    with pytest.raises(ValueError):
        pipe._audit(draft, {"returns-within-30-days": "policy text"})


def test_audit_preserves_valid_model_decision():
    pipe = q2.SupportPipeline()
    draft = json.dumps({"action": "ESCALATE_TIER2", "kb_article": "returns-within-30-days", "customer_reply": "A specialist will help."})
    result = pipe._audit(draft, {"returns-within-30-days": "policy text"})
    assert asdict(result) == {"action": "ESCALATE_TIER2", "kb_article": "returns-within-30-days"}
