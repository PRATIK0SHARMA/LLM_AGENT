# Demo video outline: about 5–7 minutes

Use your own wording. Understand the code and rerun the commands before recording. Do not present simulator measurements as real-provider spending or claim a payment or shipment was performed.

## 0:00–0:45 — State the problem

Show the two question specifications. Explain that the existing ShopAssist agent is correct but expensive. It must preserve `action` and `kb_article` while meeting a per-ticket budget: 3,000 for Q1 and 2,500 for Q2.

## 0:45–1:30 — Explain billing and the baseline

Open `shared/billing.py` and `results/baseline.json`. Explain input at 3 points, cached input at 0.3, and output at 15. Show the baseline's unnecessary verbose output and repeated context. Mention that this is a local simulator and needs no API key.

## 1:30–2:30 — Show the Q1 change

Open `question1/agent.py`. Point to compact JSON, complete five-policy context, concise output instructions, preserved snapshot markers, and exactly one `chat` call. Explain why you kept the subscription article and all order facts.

Run:

```bash
python question1/run.py
```

Explain that 6,930 is the four-ticket total, not the per-ticket figure.

## 2:30–3:45 — Show the Q2 change

Open `question2/agent.py`. Trace `_triage`, `_retrieve`, `_compose`, `_audit`. Explain that Python selects topics, loads actual policies, and validates output, while the model performs composition. All four stages still run. Be explicit that the audit checks structure/citations, not full semantic correctness.

Run:

```bash
python question2/run.py
```

Show the damaged custom item: both damage and customization policies are available, so retrieval does not lose the exception.

## 3:45–4:45 — Show measured evidence

Run:

```bash
python benchmark.py --output results/my-run.json
```

Show Q1 T-1001 and Q2 T-1001/T-1002. Explain one arithmetic example: `275*3 + 46*15 = 1515`. Show zero cached tokens. Both required Q2 paths are covered: physical refund and digital denial.

## 4:45–5:45 — Show tests and limitations

Run the quick added suite:

```bash
python -m pytest -q tests/test_optimized.py
```

Show 39 passing checks and point out subscription/boundary/unseen-ID tests. Explain why the two original baseline-cost assertions fail after successful optimization. Do not say an unfiltered test run is fully green.

The original corpus-size test can take minutes. Run the full or filtered suite before recording, then show its saved terminal result if desired; do not pretend that a prerecorded result is a new run.

Mention that the simulator uses reference rules internally, and real-model accuracy would need separate evaluation. Show that your agents do not import the grading reference.

## Finish — Show your repository

Show the README, short write-up, measured JSON, and source files in your own GitHub repository. Ensure the video link is accessible to the recruiter. Submit both required links yourself via the requested channel.

On Windows without activation, prefix each command with `.\.venv\Scripts\python.exe` instead of `python`.
