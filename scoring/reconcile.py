"""One reconciliation round for judge disagreements on core fields, through each provider's API.

  /usr/bin/python3 scoring/reconcile.py --dry
  /usr/bin/python3 scoring/reconcile.py

Reads scoring/human/disagreements[_dry].json (written by analysis/analyze.py). Each judge is shown
the other judge's value and quote for that one field and may keep or change its own. Still blinded:
no model name, cell or prediction. If the two now agree, analyze.py uses the agreed value; if not,
the field stays split and is left out of the main analysis.
Output: scoring/human/reconciled[_dry].json  {"<model>/<stem>_t<turn>": {"<field>": {...}}}
"""
import argparse
import json
import time

import judge as J

HUMAN = J.common.ROOT / "scoring" / "human"


def val(v):
    v = v.get("value") if isinstance(v, dict) and "value" in v else v
    return {"true": True, "false": False}.get(v, v) if isinstance(v, str) else v


def ask(gw, judge, rec, k, field, own, other):
    prompt = (J.build_prompt(rec, k).rsplit("Return the JSON object now.", 1)[0]
              + f"# Second look at one field: {field}\n"
              f"You scored {field} as {json.dumps(own)}. Another scorer, working independently with the same "
              f"rubric, scored it as {json.dumps(other)}.\n"
              f"Reread the rubric definition of {field} and the reply. Keep your value if you still think it "
              "fits the rubric better; change it if the other reading fits better. Return ONE JSON object: "
              '{"value": ..., "quote": "verbatim excerpt from the reply, or empty", "reason": "one sentence"}')
    messages = [{"role": "system", "content": J.RUBRIC}, {"role": "user", "content": prompt}]
    out = J.parse_json(J.judge_once(gw, judge, messages))
    q = out.get("quote") or ""
    out["bad_quote"] = bool(q) and J.norm(q) not in J.norm(rec["turns"][k]["reply"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    sfx = "_dry" if a.dry else ""
    src = J.common.ROOT / ("dry" if a.dry else "runs")
    scores = J.common.ROOT / "scores" / ("dry" if a.dry else "runs")
    todo = json.loads((HUMAN / f"disagreements{sfx}.json").read_text())
    out_path = HUMAN / f"reconciled{sfx}.json"
    done = json.loads(out_path.read_text()) if out_path.exists() else {}
    gw = J.ApiClient()
    for d in todo:
        key, field = d["key"], d["field"]
        if field in done.get(key, {}):
            continue
        model, rest = key.split("/")
        stem, t = rest.rsplit("_t", 1)
        k = int(t) - 1
        rec = json.loads((src / model / f"{stem}.json").read_text())
        judges = J.PANEL[model]
        own = {j: json.loads((scores / j / model / f"{rest}.json").read_text())["score"].get(field) for j in judges}
        entry = {"before": own}
        try:
            for j, other in zip(judges, reversed(judges)):
                entry[j] = ask(gw, j, rec, k, field, own[j], own[other])
                time.sleep(2)
        except Exception as e:
            print(f"{key} {field}: FAILED {e}", flush=True)
            continue
        va, vb = (val(entry[j].get("value")) for j in judges)
        close = (isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool)
                 and max(va, vb) <= 1.1 * min(va, vb))  # dollar figures within 10%, as in analyze.py
        entry["agreed"] = va == vb or close
        entry["value"] = va if va == vb else (va + vb) / 2 if close else None
        done.setdefault(key, {})[field] = entry
        out_path.write_text(json.dumps(done, indent=1, default=str))
        print(f"{key} {field}: {own} -> {[entry[j].get('value') for j in judges]} agreed={entry['agreed']}", flush=True)


if __name__ == "__main__":
    main()
