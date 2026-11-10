"""Scores every reply with two judges from the other two model families, through each provider's API.

  /usr/bin/python3 scoring/judge.py --dry          # score dry/ (calibration)
  /usr/bin/python3 scoring/judge.py                # score runs/

Subject gpt -> judges claude + gemini; gemini -> claude + gpt; claude -> gpt + gemini.
Judges see the candidate's messages and the reply only: no model name, cell or prediction.
Every quote must be a verbatim substring of the reply; failures get one retry, then are flagged.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))
import common  # noqa: E402
from run_gpt_gemini import ApiClient  # noqa: E402  network client omitted

JUDGES = {
    "claude": dict(model_id="claude-opus-4-8", body={"max_tokens": 8000}),
    "gpt": dict(model_id="gpt-5.6-sol", body={"max_completion_tokens": 20000}),
    "gemini": dict(model_id="gemini-3.7-flash", body={"max_tokens": 16000}),
}
PANEL = {"gpt": ["claude", "gemini"], "gemini": ["claude", "gpt"], "claude": ["gpt", "gemini"]}
RUBRIC = (common.ROOT / "scoring" / "rubric.md").read_text()
EMPTY = {False, None, "", "false", "none", "not_discussed", "not_stated", "not_done", "n/a"}
BRANDS = re.compile(r"\b(ChatGPT|OpenAI|GPT-?[\d.]+\w*|Gemini|Bard|Claude|Anthropic)\b", re.I)


def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("—", "-").replace("–", "-").replace("**", "").replace("\\$", "$")
    return re.sub(r"\s+", " ", s).strip().lower()


def blind(text):
    return BRANDS.sub("[assistant]", text)


def build_prompt(rec, k):
    parts = ["# Conversation so far"]
    for i, t in enumerate(rec["turns"][: k + 1]):
        parts.append(f"## Candidate message {i + 1}\n{t['user']}")
        if i < k:
            parts.append(f"## Assistant reply {i + 1} (context only, do not score)\n{blind(t['reply'])}")
    parts.append(f"# Reply to score\n{blind(rec['turns'][k]['reply'])}")
    parts.append("Return the JSON object now.")
    return "\n\n".join(parts)


def parse_json(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON object in judge output")
    return json.loads(m.group(0))


def bad_quotes(score, reply):
    r = norm(reply)
    bad = []
    for field, v in score.items():
        items = v if field == "unsupported_claims" and isinstance(v, list) else [v]
        for it in items:
            if not isinstance(it, dict) or "quote" not in it:
                continue
            q = it.get("quote") or ""
            if field != "unsupported_claims" and it.get("value") in EMPTY and not q:
                continue
            if not q or norm(q) not in r:
                bad.append(field)
    return sorted(set(bad))


def judge_once(gw, judge, messages):
    j = JUDGES[judge]
    out = gw.post("chat/completions", j["model_id"], {"messages": messages, **j["body"]})
    content = out["choices"][0]["message"].get("content") or ""
    if isinstance(content, list):
        content = "".join(p.get("text", "") for p in content)
    return content


def score_turn(gw, judge, rec, k):
    reply = rec["turns"][k]["reply"]
    messages = [{"role": "system", "content": RUBRIC}, {"role": "user", "content": build_prompt(rec, k)}]
    text = judge_once(gw, judge, messages)
    score = parse_json(text)
    bad = bad_quotes(score, reply)
    retried = False
    if bad:
        retried = True
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": "These fields have quotes that are not exact substrings of the "
                      f"reply: {', '.join(bad)}. Copy the quotes character for character from the reply (or fix "
                      "the value). Return the full corrected JSON object."}]
        text = judge_once(gw, judge, messages)
        score = parse_json(text)
        bad = bad_quotes(score, reply)
    return dict(score=score, bad_quotes=bad, retried=retried)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--models", default="gpt,gemini,claude")
    a = ap.parse_args()
    src = common.ROOT / ("dry" if a.dry else "runs")
    dst = common.ROOT / "scores" / ("dry" if a.dry else "runs")
    gw = ApiClient()
    for model in a.models.split(","):
        for f in sorted((src / model).glob("*_r[0-9][0-9].json")):
            rec = json.loads(f.read_text())
            for k in range(len(rec["turns"])):
                for judge in PANEL[model]:
                    out = dst / judge / model / f"{f.stem}_t{k + 1}.json"
                    if out.exists():
                        continue
                    out.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        res = score_turn(gw, judge, rec, k)
                    except Exception as e:
                        print(f"{judge} on {model}/{f.stem} t{k + 1}: FAILED {e}", flush=True)
                        continue
                    res.update(judge=judge, judge_model=JUDGES[judge]["model_id"], subject=model,
                               cell=rec["cell"], rep=rec["rep"], turn=k + 1, at=common.now())
                    out.write_text(json.dumps(res, indent=1))
                    print(f"{judge} on {model}/{f.stem} t{k + 1}: ok bad_quotes={res['bad_quotes']}", flush=True)
                    time.sleep(2)


if __name__ == "__main__":
    main()
