# ShopAssist optimization write-up

## Scope

Source revision: `d9989e294615046519a1658ff76c4343f465fb0c` of https://github.com/Induseuro-labs/intern-assignment-llm-cost-optimization.

Only `question1/agent.py` and `question2/agent.py` modify existing runtime code. Billing, tokenizer, simulator, fixtures, policy files, reference implementation, and original tests are unchanged. Added files provide benchmarks, regression tests, and explanation.

## Q1 approach

Keep exactly one `LlmClient.chat` call. Request only the required JSON and a short customer reply. Remove the random run ID and redundant examples. Compact the order JSON without dropping any facts. Keep the entire small five-article KB, including the subscription policy, and retain the original return contract/parser.

Output tokens cost five times ordinary input tokens, so avoiding the baseline's long narrative is the largest saving. Stable prompts are useful, but no cache savings are claimed.

## Q2 approach

Preserve triage → retrieve → compose → audit as four executed methods:

| Stage | Implementation | Why |
| --- | --- | --- |
| Triage | Local order-metadata-to-policy-topic selection | Already structured facts do not need an LLM restatement |
| Retrieve | Read selected real Markdown articles | Loading known files does not need text generation |
| Compose | One concise LLM call with facts, thread, and policies | Retain model-based decision and reply generation |
| Audit | Local JSON, action, citation, and reply validation | Output contract checks are deterministic |

The general returns policy remains available as fallback. Customization, damage, digital-license, and subscription topics are included when applicable; unknown product categories receive all real articles. The four-node spec is interpreted as four stages, not a mandate for four paid model calls.

No expanded help-center blob is constructed by the optimized agent. Its repeated routing filler supplies no additional customer policy in this repository. No answer is selected by ticket ID. Neither agent directly imports `eval/reference.py`.

## Measured results

Each row uses a new agent and fresh `CostSession`; cached input is zero. Values below come from `results/baseline.json` and `results/optimized.json`. Baseline UUIDs make its exact counts vary slightly across runs.

| Ticket | Q1 baseline | Q1 optimized | Q2 baseline | Q2 optimized |
| --- | ---: | ---: | ---: | ---: |
| T-1001 | 8,862 | 1,854 | 73,410 | 1,515 |
| T-1002 | 8,769 | 1,731 | 73,098 | 1,389 |
| T-1003 | 8,898 | 1,692 | 73,080 | 1,461 |
| T-1004 | 8,919 | 1,653 | 73,296 | 1,314 |
| T-1091 | 8,928 | 1,695 | 73,392 | 1,371 |

All public Q1 tickets meet 3,000 points; all public Q2 tickets meet 2,500 points. The subscription fixture also remains correct and fits the corresponding budgets. Public-ticket reductions in this measured run are approximately 79–81% for Q1 and 98% for Q2.

### Required per-call breakdowns

| Track/ticket | Call | Uncached input | Cached input | Output | Points |
| --- | --- | ---: | ---: | ---: | ---: |
| Q1 / T-1001 | handle_ticket | 388 | 0 | 46 | 1,854 |
| Q2 / T-1001, physical refund | compose | 275 | 0 | 46 | 1,515 |
| Q2 / T-1002, digital denial | compose | 268 | 0 | 39 | 1,389 |

For Q2, triage, retrieval, and audit make zero LLM calls and incur zero points under this accounting model. Local CPU and file I/O are not included in the repository's LLM points metric.

Calculations:

- Q1 T-1001: `388*3 + 0*0.3 + 46*15 = 1854`.
- Q2 T-1001: `275*3 + 0*0.3 + 46*15 = 1515`.
- Q2 T-1002: `268*3 + 0*0.3 + 39*15 = 1389`.

### Baseline call breakdown for comparison

| Track/ticket | Call | Input (all uncached) | Output | Points |
| --- | --- | ---: | ---: | ---: |
| Q1 / T-1001 | handle_ticket | 524 | 486 | 8,862 |
| Q2 / T-1001 | triage | 8,456 | 488 | 32,688 |
| Q2 / T-1001 | retrieve | 596 | 46 | 2,478 |
| Q2 / T-1001 | compose | 1,193 | 484 | 10,839 |
| Q2 / T-1001 | audit | 6,715 | 484 | 27,405 |

## Validation and reproducibility

Tested with Python 3.12, pytest 9.2.0, and tiktoken 0.14.0. The dependencies are those requested by the original `requirements.txt`.

From the repository root, using your environment's Python:

```bash
python -m pip install -r requirements.txt
python question1/run.py
python question2/run.py
python benchmark.py --output results/my-run.json
python -m pytest -q tests/test_optimized.py
python -m pytest -q -k "not baseline_cost_is_high"
```

The new suite has 39 passing checks. It validates both agents on all five supplied tickets, one call per ticket, individual budgets, zero claimed cache tokens, complete order preservation, unseen IDs with changed facts, 7/8-day damage and 30/31-day return/subscription boundaries, custom/digital exceptions, unknown-category retrieval, and malformed-output rejection.

The untouched upstream suite passed all six tests before optimization. After optimization, its two `test_baseline_cost_is_high` assertions intentionally cease to hold: Q1 now costs 6,930 total points for four public tickets, and Q2 T-1001 now costs 1,515. These tests demand the expensive baseline, not the requested optimized budget. They are preserved, not weakened or hidden. Run the filtered command above to omit only those obsolete baseline-cost assertions; the new tests enforce the required upper bounds.

To reproduce baseline measurements, use a separate checkout at the source revision, copy only `benchmark.py` into it, and run the benchmark there. Do not overwrite the recorded baseline with an optimized run. Constructing the original huge corpus can take several minutes.

## Limitations and tradeoffs

- The simulator internally decides from structured order facts through its reference rules. These tests do not measure real-LLM comprehension, output reliability, or robustness to malicious customer text.
- The local audit checks structure and citation membership. It is not an independent semantic proof that the selected action is policy-compliant.
- The metadata routing covers the supplied policy categories. A real large KB needs indexed retrieval, versioning, recall evaluation, and an unknown-topic strategy.
- All original order fields and the full customer thread are preserved. Arbitrarily long threads or the simulator's verbosity-trigger phrases could exceed the measured fixture budgets.
- No cache discount is assumed. The client exposes prefix accounting, but does not model real cold/warm cache history.
- In production, a generated refund/replacement approval must be connected to verified transaction tools. This exercise only returns resolutions.

See `WALKTHROUGH.md` for beginner-oriented explanations and Windows setup. See `DEMO_GUIDE.md` for a video outline.
