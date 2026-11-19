# ShopAssist — support copilot cost lab

**ShopAssist** is a Tier-1 support agent for an e-commerce company. For each ticket it:

1. Reads the customer thread (`data/tickets/`)
2. Loads order facts (`data/orders/` via `shared/tools.py`)
3. Picks an action (`REFUND`, `REPLACE`, `SEND_ARTICLE`, `ESCALATE_TIER2`)
4. Cites the help-center article that backs the decision (`data/kb/`)

| Track | Code | Spec |
|-------|------|------|
| Q1 — single call | [question1/agent.py](question1/agent.py) | [questions/question-1.md](questions/question-1.md) |
| Q2 — pipeline | [question2/agent.py](question2/agent.py) | [questions/question-2.md](questions/question-2.md) |

## Run

```bash
pip install -r requirements.txt
pytest -q
python question1/run.py
python question2/run.py
```

`shared/llm.py` provides a local `LlmClient` with the same billing accounting you would use against a hosted chat API. Do not import `eval/reference.py` from your agent.

## Billing

| Input | Cached input | Output |
|------:|-------------:|-------:|
| 3 | 0.3 | 15 |

Cached input = identical prefix ≥ 1024 tokens across calls.

```
points = uncached_input × 3 + cached_input × 0.3 + output × 15
```

Per-call details are in `shared/billing.py` (`CostSession` on your agent).

## Optimized solution

The optimized implementations retain the graded decisions and score below both per-ticket targets. Start with [the walkthrough](WALKTHROUGH.md), then review [the write-up and measured breakdowns](SOLUTION.md).

- Q1: one concise model call; complete small KB; compact order JSON.
- Q2: four stages with local triage, targeted file retrieval, one model compose call, and local output validation.
- [Measured baseline](results/baseline.json) and [optimized results](results/optimized.json).
- [Video demonstration outline](DEMO_GUIDE.md).

```bash
python benchmark.py --output results/my-run.json
python -m pytest -q tests/test_optimized.py
python -m pytest -q -k "not baseline_cost_is_high"
```

The two original `test_baseline_cost_is_high` tests are preserved. They assert that the original implementation is expensive and therefore fail after optimization. The filtered command excludes only those two assertions; the added tests enforce the required per-ticket upper bounds. The full unfiltered suite is not expected to pass those obsolete baseline-cost assertions. The original large-corpus test may take several minutes.

These are local simulator measurements, with no cached-token discount. The Q2 audit validates output structure and citation membership, not full policy semantics. See the write-up for limitations.
