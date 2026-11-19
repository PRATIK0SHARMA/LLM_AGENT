# ShopAssist: understand and solve both questions

This guide accompanies working solutions for Induseuro Labs' LLM cost optimization assignment. The inspected upstream revision is `d9989e294615046519a1658ff76c4343f465fb0c`.

Source: https://github.com/Induseuro-labs/intern-assignment-llm-cost-optimization

## 1. What are you actually building?

ShopAssist is a small customer-support copilot. A customer asks for a refund or replacement. Your code reads the conversation and order, supplies the applicable policies to a model, and returns a decision and the policy that supports it.

You are improving existing working software. You do not need to train an LLM, build a website, obtain an API key, or add an agent framework. This repository already supplies a Python LLM simulator.

Both tasks ask you to keep the same routing decisions while spending fewer simulated billing points.

| Question | Starting class | Required public-ticket budget |
| --- | --- | --- |
| Q1 | `question1/agent.py`: `SupportCopilot` | At most 3,000 points for each ticket; one LLM call per ticket |
| Q2 | `question2/agent.py`: `SupportPipeline` | At most 2,500 points for each ticket; retain triage, retrieve, compose, audit |

The scored fields are `action` and `kb_article`. Parsing must still work. Q1 also retains a customer reply and raw completion in its existing return object. Q2 retains its original public return object with two fields.

## 2. Vocabulary in ordinary language

- **LLM:** the model that reads text and generates text.
- **Prompt:** the messages sent to the model.
- **Input tokens:** pieces of text in the prompt; tokens are not necessarily words.
- **Output tokens:** pieces of text the model generates.
- **KB:** knowledge base, here the Markdown help-center policy files.
- **Retrieval:** selecting and loading relevant policies before asking the model.
- **Pipeline node:** a stage in a program. A node does not automatically need an LLM.
- **JSON:** structured text with named fields, which Python can parse reliably.
- **Baseline:** the original working implementation, used for comparison.
- **Regression:** a previously correct behavior that breaks after your edit.

## 3. Know the folder structure before editing

| Path | Purpose | What to do |
| --- | --- | --- |
| `questions/question-1.md` | Q1 requirements | Read |
| `questions/question-2.md` | Q2 requirements | Read |
| `question1/agent.py` | Single-call solution | Replace with the supplied optimized version |
| `question2/agent.py` | Four-stage solution | Replace with the supplied optimized version |
| `question1/run.py`, `question2/run.py` | Demo entry points | Run; no edits needed |
| `data/tickets/` | Customer conversations and order references | Read; leave unchanged |
| `data/orders/` | Structured order facts | Read; leave unchanged |
| `data/kb/` | Actual support policies | Read; leave unchanged |
| `shared/tools.py` | Loads ticket/order JSON and formats conversations | Use; leave unchanged |
| `shared/kb.py` | Loads articles and constructs the expanded Q2 corpus | Use targeted loaders; leave unchanged |
| `shared/llm.py` | Local simulated LLM | Understand; leave unchanged |
| `shared/tokens.py` | Token counting | Leave unchanged |
| `shared/billing.py` | Points accounting | Leave unchanged |
| `eval/reference.py` | Grading rules used internally by the simulator | Do not import from solution agents or copy its answer table |
| `tests/test_question1.py`, `tests/test_question2.py` | Original tests | Preserve, including the baseline-cost assertions |
| `tests/test_optimized.py` | Added correctness and budget checks | Add |
| `benchmark.py` | Prints actual per-call token and cost evidence | Add |
| `results/` | Recorded benchmark evidence | Include with write-up |
| `SOLUTION.md` | Short technical write-up | Read and adapt for submission |

Only the two `agent.py` files change existing tracked runtime code. Everything else added is documentation, tests, or measurement support.

## 4. Understand the supplied scenarios

| Ticket | Facts | Expected action | Article |
| --- | --- | --- | --- |
| T-1001 | Unopened physical headphones, delivered 10 days ago | REFUND | returns-within-30-days |
| T-1002 | Ebook license already revealed | SEND_ARTICLE | digital-license-no-refund |
| T-1003 | Damaged personalized mug | ESCALATE_TIER2 | custom-items-no-replace |
| T-1004 | Damaged standard mug, delivered 2 days ago | REPLACE | damage-replacement-7-days |
| T-1091 | Subscription cancellation on day 38 | SEND_ARTICLE | subscription-cooling-off |

`SEND_ARTICLE` means explaining the applicable policy instead of granting the requested refund. `ESCALATE_TIER2` means handing the case to a specialist. The code does not actually issue payments or ship goods.

T-1091 appears in a test named holdout, but its fixture is visible in the repository. Preserve it; do not optimize only for the four public IDs.

## 5. Understand how points work

The assignment uses synthetic points, not rupees or a provider invoice:

```
points = uncached_input_tokens * 3
       + cached_input_tokens * 0.3
       + output_tokens * 15
```

One output token costs as much as five ordinary input tokens. Removing unnecessary generated commentary is therefore particularly valuable.

Example from the optimized Q1 implementation, T-1001:

```
input = 388 tokens; cached input = 0; output = 46 tokens
points = 388 * 3 + 46 * 15 = 1,854
```

The budget is per ticket. A low average cannot compensate for one ticket exceeding its limit. `run.py` prints the total for four tickets; do not compare that total to the single-ticket limit.

### Why this solution does not claim cache savings

The README describes an identical-prefix cache with a 1,024-token minimum. The local client requires an explicit `cached_prefix` and checks whether it starts the serialized prompt. It does not implement a real history-aware cache with measured cold and warm requests.

The optimized prompts are shorter than 1,024 tokens, and the solution never passes `cached_prefix`. All measured cache counts are zero. Removing random run IDs makes prompts stable, but it does not by itself create billed cache hits. Do not add padding just to qualify for a discount.

## 6. What is making the original implementation expensive?

### Q1

The original system prompt includes a random UUID, examples that repeat policy information, all five articles, and a request for long explanatory output. Its order JSON is pretty-printed.

In this simulator, specific prompt phrases trigger a response of at least 480 tokens. That generated text alone costs at least 7,200 points, already above Q1's target. Requesting only the necessary JSON removes that unnecessary output path.

### Q2

The original code asks the model to do all four stages. It includes huge help-center slices, repeats triage output, and copies prior outputs into later prompts. A large first response becomes expensive input for the next call as well.

The expanded help center has more than 200,000 tokens, but the supplied implementation builds most of it from repeated internal routing notes. Those notes explicitly do not change customer policy. The real policies live in five small Markdown files.

Passing arbitrary character slices is also fragile: character count is not token count, and truncation can omit relevant material in a genuine corpus.

## 7. Q1: explain every implementation step

Open `question1/agent.py`.

### Step 1: Keep the existing output contract and parser

`TicketResolution` still contains `action`, `kb_article`, `customer_reply`, and `raw_completion`. `parse_resolution` is retained. Existing callers and the grading code therefore receive the same shape.

The parser finds the JSON object, decodes it, normalizes the action to uppercase, and builds the dataclass. The new prompt asks for JSON only, but the old tolerant parsing remains available.

### Step 2: Preserve the supplied billing session

The constructor still creates or accepts `CostSession` and passes it to `LlmClient`. Every model call is measured through the original accounting implementation. No points are hidden or overwritten.

### Step 3: Load the actual ticket and its order

`get_ticket(ticket_id)` reads the conversation. `get_order(ticket["order_id"])` follows its order reference. This works for new IDs; it does not use an ID-to-answer dictionary.

### Step 4: Compact the order JSON

```python
snapshot = json.dumps(order, separators=(",", ":"))
```

The separators remove optional spaces after commas and colons. All fields, booleans, and numbers survive. This is safer than guessing which facts can be deleted and accidentally dropping `subscription_age_days`.

### Step 5: Use a stable, focused system prompt

The prompt specifies the support task, allowed actions, required JSON fields, short reply, and how to handle unsupported cases. It treats the customer conversation as data.

Random UUIDs and repeated examples are removed because they add tokens without supplying new facts. Removing the examples is reasonable here because the complete small policy set remains in the prompt.

### Step 6: Keep all five real policies

`all_articles_blob()` is retained for Q1. The small KB is cheap enough to fit below the target, and preserving it avoids discarding the subscription exception. Optimization is about removing waste, not minimizing every last token.

### Step 7: Preserve the simulator's snapshot markers

```
ORDER_SNAPSHOT:
{...order JSON...}
END_SNAPSHOT
```

`shared/llm.py` extracts the order between these exact markers. Renaming or deleting them breaks the simulator even if a real LLM could understand the prompt.

### Step 8: Make exactly one model call and parse it

`handle_ticket` builds messages, calls `self.llm.chat` once, and returns the parsed result. There are no answer substitutions or extra uncounted model calls.

## 8. Q2: explain every implementation step

Open `question2/agent.py`.

The flow is still triage → retrieve → compose → audit. The specification names four stages; it does not explicitly require four LLM calls. This solution interprets a stage as a responsibility that can be implemented in Python. Document this design decision clearly.

### Step 1: Load the ticket and order once

`handle_ticket` reads both objects, then passes information directly between stages. It does not generate a prose restatement and repeatedly copy it into later prompts.

### Step 2: Triage selects topics in ordinary Python

`_triage(order)` creates a `TriageResult`, a small immutable dataclass containing candidate article IDs.

The general returns policy is always included. Subscription orders add the subscription article. Digital or revealed-license orders add the digital article. Customized orders add the custom-item exception. Physical or damaged orders add the damage policy. Unknown product categories receive all real articles.

These checks choose evidence; they do not choose a refund, replacement, denial, or escalation. No ticket IDs are checked. The model still returns the action.

The checks can add several policies, which is intentional. A customized damaged item needs both the damage policy and the exception that prevents automatic replacement.

Sorting the set gives a stable article order. An unknown category uses `article_ids()` so it receives broad policy coverage rather than an arbitrary partial selection.

### Step 3: Retrieval reads actual files

`_retrieve` calls `load_article(aid)` for each candidate. It returns a dictionary mapping IDs to policy text.

A model is not needed to read a known file. The program avoids constructing or sending the expanded filler corpus altogether. Because the supplied articles are short, full relevant policies fit comfortably in the prompt.

For a genuine large KB, replace these explicit topic mappings with indexed search and test retrieval recall. This small solution is tailored to the supplied repository, not a universal retrieval system.

### Step 4: Compose makes the only LLM call

`_compose` sends the actual thread, complete compact order, and selected policy text. It requests the same concise JSON contract as Q1.

Each piece of information is sent once. No duplicated triage narrative, no arbitrary giant KB slice, and no full previous chain transcript are needed.

### Step 5: Audit validates the contract locally

`_audit` parses JSON and checks:

1. The result is an object.
2. The action is a supported string.
3. The cited article is one that retrieval supplied.
4. A nonempty customer reply exists.

It returns the original two-field Q2 `TicketResolution`. Invalid output raises an error rather than silently fabricating a decision.

This is a structural and citation audit, not a full semantic policy audit. It cannot prove that the action is justified merely because the cited article exists. A real production system needs separately evaluated decision validation, controlled retries or human review, and truthful transactional wording. Those extensions are outside the measured local solution.

## 9. Important simulator limitation

`LlmClient.chat` reads the snapshot and internally invokes the supplied reference decision function. It does not genuinely reason over the policy prose. Its verbose/concise behavior is also controlled by phrase matching.

Consequences:

- Passing tests demonstrates compatibility with this simulator and its cost accounting.
- It does not establish real-model decision accuracy or prompt-injection resistance.
- Keeping all facts and relevant policies is still good design, even though the simulator could return correct answers without reading those policies.
- The solution agents must not directly import the reference decision function or return its lookup-table answers. These agents do neither.
- Customer text containing a verbosity-trigger phrase can increase simulated output. The submitted budgets cover the supplied fixtures; arbitrary long/adversarial conversations are not guaranteed to meet them.

## 10. Run it on Windows with VS Code

### Option A: use the supplied complete ZIP

Extract `ShopAssist_Optimized_Solution.zip`. Open the extracted `ShopAssist_Optimized_Solution` folder in VS Code. It contains the original repository files plus the solution and documentation. The ZIP excludes `.git`, virtual environments, and Python caches.

### Option B: use your own fork

Fork the upstream repository on GitHub. Clone your fork locally. Copy the two optimized `agent.py` files into the matching folders; add `benchmark.py`, `tests/test_optimized.py`, and the documentation/results files.

Do not accidentally paste Q2 into Q1 or put both agents into one file. Do not edit files directly in the company's repository.

### Create an environment from the repository root

In the VS Code terminal, with Python installed:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The explicit interpreter path avoids PowerShell activation-script restrictions. This work was tested on Python 3.12. On macOS/Linux, use `python3 -m venv .venv` and `.venv/bin/python` in place of the Windows interpreter path.

### Run demos and tests

```powershell
.\.venv\Scripts\python.exe question1/run.py
.\.venv\Scripts\python.exe question2/run.py
.\.venv\Scripts\python.exe benchmark.py --output results/my-run.json
.\.venv\Scripts\python.exe -m pytest -q tests/test_optimized.py
.\.venv\Scripts\python.exe -m pytest -q -k "not baseline_cost_is_high"
```

The first install/tokenizer initialization may need internet. Normal model calls are local and need no API key. The original large-corpus test can be slow because it repeatedly tokenizes a growing string.

### Understand the two original baseline-cost tests

The original Q1 cost test expects the four-ticket total to exceed 15,000. The original Q2 cost test expects T-1001 to exceed 70,000. These characterize the expensive baseline and contradict the optimization objectives.

The supplied solution preserves them unchanged. A full `pytest -q` therefore has two expected failures after optimization. The command with `-k "not baseline_cost_is_high"` excludes only those two named baseline assertions. The added tests assert the required upper limits separately for every ticket, so skipping the obsolete lower-bound assertions does not remove budget validation.

Explain this explicitly in your README and demo. Do not claim all unmodified tests pass or manipulate billing to satisfy both incompatible conditions.

## 11. Verify and submit work you can explain

Check the benchmark's action and article, not just its points. Open `results/optimized.json` to inspect every call. `SOLUTION.md` includes required breakdowns and measured comparisons; `DEMO_GUIDE.md` provides a recording outline.

Before committing, review changed files with `git diff` and the status with `git status`. Keep `.venv`, caches, secrets, and credentials out of Git. If using the ZIP instead of a fork, initialize your own repository before committing and connect it to an empty repository you own. If using a fork, preserve the existing Git history.

Upload the solution to your repository, record yourself running the code and explaining these choices, then submit your repository and video links using the recruiter's requested channel. The advertised deadline in the message you supplied is 20 November 2026. Submission and video recording are still your next steps; no message or application has been sent.
