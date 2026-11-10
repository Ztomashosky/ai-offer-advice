"""Runs the Claude cells on the Anthropic API, web search on.

Same procedure as run_gpt_gemini.py: same system prompt, prompts, plan and record format.
Needs the official SDK:  python3 -m venv .venv && .venv/bin/pip install anthropic
Key: ANTHROPIC_API_KEY, or ANTHROPIC_API_KEY=... in ~/.config/anthropic/.env (never in this repo).

  .venv/bin/python harness/run_claude.py --dry
  .venv/bin/python harness/run_claude.py --wave 1
  .venv/bin/python harness/run_claude.py --wave 2 --cells A3,A4

No refusal fallback is enabled: a fallback would answer with a different model, so a refusal is
recorded as a refusal.
"""
import argparse
import os
import sys
import time
from pathlib import Path

import anthropic

import common

MODEL_ID = "claude-opus-5-5"
TOOLS = [{"type": "web_search_20260209", "name": "web_search"}]
MAX_CONTINUATIONS = 5
PAUSE = 4


def load_key():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return os.environ["ANTHROPIC_API_KEY"]
    env = Path.home() / ".config" / "anthropic" / ".env"
    for line in env.read_text().splitlines():
        if line.startswith("ANTHROPIC_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("No ANTHROPIC_API_KEY found")


def web_searches(usage):
    st = getattr(usage, "server_tool_use", None)
    return (getattr(st, "web_search_requests", 0) or 0) if st else 0


def claude_send(client):
    def send(messages):
        system = messages[0]["content"]
        convo = [m for m in messages[1:]]
        raws, text, searches, cites = [], [], [], []
        usage = {"input": 0, "output": 0, "web_searches": 0}
        for _ in range(MAX_CONTINUATIONS):
            r = client.messages.create(model=MODEL_ID, max_tokens=16000, system=system,
                                       messages=convo, tools=TOOLS)
            raws.append(r.to_dict())
            usage["input"] += r.usage.input_tokens
            usage["output"] += r.usage.output_tokens
            usage["web_searches"] += web_searches(r.usage)
            for b in r.content:
                if b.type == "text":
                    text.append(b.text)
                    cites += [c.url for c in (getattr(b, "citations", None) or []) if getattr(c, "url", None)]
                elif b.type == "server_tool_use" and b.name == "web_search":
                    searches.append({"query": b.input.get("query")})
            if r.stop_reason != "pause_turn":
                break
            convo = convo + [{"role": "assistant", "content": r.content}]  # server resumes
        return dict(reply="".join(text).strip(), searches=searches, citations=sorted(set(cites)),
                    usage=usage, finish=r.stop_reason, served_model=r.model, raw=raws)
    return send


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wave", type=int, default=1)
    ap.add_argument("--cells", help="comma list; default all cells")
    ap.add_argument("--dry", action="store_true", help="uncounted dry run into dry/")
    a = ap.parse_args()

    client = anthropic.Anthropic(api_key=load_key(), max_retries=4)
    (common.ROOT / "runs").mkdir(exist_ok=True)
    send = claude_send(client)
    jobs = common.dry_plan() if a.dry else common.plan("claude", a.wave, a.cells and a.cells.split(","))
    counts = {}
    for i, (cell, rep) in enumerate(jobs, 1):
        st = common.run_chat(send, "claude", MODEL_ID, "API", cell, rep,
                             0 if a.dry else a.wave, dry=a.dry)
        counts[st] = counts.get(st, 0) + 1
        print(f"[{i}/{len(jobs)}] claude {cell} r{rep}: {st}", flush=True)
        if st != "skip":
            time.sleep(PAUSE)
    print("done", counts)


if __name__ == "__main__":
    main()
