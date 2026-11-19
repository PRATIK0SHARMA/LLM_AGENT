"""Measure fresh-session, per-ticket costs without changing the billing code."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from question1.agent import SupportCopilot
from question2.agent import SupportPipeline

TICKETS = ["T-1001", "T-1002", "T-1003", "T-1004", "T-1091"]


def measure() -> list[dict]:
    rows = []
    for track, cls in [("Q1", SupportCopilot), ("Q2", SupportPipeline)]:
        for ticket_id in TICKETS:
            agent = cls()
            result = agent.handle_ticket(ticket_id)
            rows.append({
                "track": track,
                "ticket_id": ticket_id,
                "action": result.action,
                "kb_article": result.kb_article,
                "total_points": agent.session.total_points(),
                "calls": [{
                    "label": call.label,
                    "input_tokens": call.input_tokens,
                    "cached_input_tokens": call.cached_prefix_tokens,
                    "uncached_input_tokens": call.input_tokens - call.cached_prefix_tokens,
                    "output_tokens": call.output_tokens,
                    "points": call.points(),
                } for call in agent.session.calls],
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(measure(), indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    print(result, end="")


if __name__ == "__main__":
    main()
