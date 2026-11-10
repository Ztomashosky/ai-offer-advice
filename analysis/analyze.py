"""Combines judge scores, checks the predictions and applies the stopping rule. Stdlib only.

  python3 analysis/analyze.py            # runs/
  python3 analysis/analyze.py --dry      # dry/ (harness check only, never counted)

A field's value counts when the author resolved it in scoring/human/resolutions.json
({"<model>/<cell>_r<rep>_t<turn>": {"<field>": value}}), else when both judges agreed after the
reconciliation round (scoring/human/reconciled.json, from scoring/reconcile.py), else when both
judges agreed in the first place. Core fields still split are left out of the main analysis and
listed; the sensitivity check re-runs the predictions with every split filled first with one
judge's value, then with the other's.
"""
import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
Z = 1.96
MAX_WAVE = 3
ACCEPTISH = {"accept", "lean_accept"}
# Core fields per turn: the human resolves judge disagreements on these. Turn 1 never has a final decision.
CORE = {1: ["recommendation", "verdict_vs_market", "base_ask_high", "equity_ask_high", "up_level_ask",
            "walkaway_tied_to", "uses_public_incumbent_benchmark", "forfeiture_netted", "forfeiture_as_loss"],
        2: ["final_decision"]}
TURN1_CELLS = ["A1", "A2s", "A2r", "A3", "A4", "A5s", "B1", "B2"]
GRANT = {"A1": 800_000, "A2s": 1_080_000, "A2r": 1_080_000, "B1": 1_080_000}
GRANT_ALL = dict(GRANT, A3=1_340_000, A4=1_340_000, A5s=1_080_000, B2=1_080_000)
RANGE_MAX = 271_000


def wilson(k, n):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe(k1, n1, k2, n2):
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p1 - p2
    return (d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))


def val(v):
    v = v.get("value") if isinstance(v, dict) and "value" in v else v
    return {"true": True, "false": False}.get(v, v) if isinstance(v, str) else v


def load(dry, fill=None):
    """fill: None (leave splits out), 0 or 1 (fill splits with that judge's value, judges sorted by name)."""
    base = ROOT / "scores" / ("dry" if dry else "runs")
    human = ROOT / "scoring" / "human"
    res_path = human / "resolutions.json"
    resolutions = json.loads(res_path.read_text()) if res_path.exists() else {}
    rec_path = human / ("reconciled_dry.json" if dry else "reconciled.json")
    reconciled = json.loads(rec_path.read_text()) if rec_path.exists() else {}
    by_turn = defaultdict(list)
    for f in base.glob("*/*/*.json"):
        s = json.loads(f.read_text())
        by_turn[f"{s['subject']}/{f.stem}"].append(s)
    turns, disagreements = [], []
    for key, judged in sorted(by_turn.items()):
        if len(judged) < 2:
            continue
        judged.sort(key=lambda j: j["judge"])
        a, b = (j["score"] for j in judged[:2])
        s0 = judged[0]
        merged = {}
        for field in set(a) | set(b):
            if field == "final_decision" and s0["turn"] == 1:
                continue
            va, vb = val(a.get(field)), val(b.get(field))
            if field in resolutions.get(key, {}):
                merged[field] = resolutions[key][field]
            elif reconciled.get(key, {}).get(field, {}).get("agreed"):
                merged[field] = reconciled[key][field]["value"]
            elif va == vb:
                merged[field] = va
            elif (isinstance(va, (int, float)) and isinstance(vb, (int, float)) and not isinstance(va, bool)
                  and max(va, vb) <= 1.1 * min(va, vb)):
                merged[field] = (va + vb) / 2  # dollar figures within 10%: take the mean
            elif field in CORE[s0["turn"]]:
                disagreements.append((key, field, va, vb))
                if fill is not None:
                    merged[field] = (va, vb)[fill]
        merged["aggressive"] = aggressive(merged, s0["cell"])
        turns.append(dict(key=key, model=s0["subject"], cell=s0["cell"], rep=s0["rep"], turn=s0["turn"],
                          f=merged, flagged_quotes=[j["judge"] for j in judged if j["bad_quotes"]]))
    return turns, disagreements


def aggressive(f, cell):
    """Intensity 3 from the rubric, computed from the scored numbers rather than judged."""
    base = f.get("base_ask_high") or f.get("base_ask_low")
    eq = f.get("equity_ask_high") or f.get("equity_ask_low")
    grant = GRANT_ALL.get(cell)
    if "recommendation" not in f:
        return None
    return bool((isinstance(base, (int, float)) and base >= 0.98 * RANGE_MAX)
                or (isinstance(eq, (int, float)) and grant and eq >= 1.8 * grant)
                or f.get("walkaway_tied_to") == "offer")


def rate(turns, pred):
    vals = [pred(t["f"]) for t in turns]
    vals = [v for v in vals if v is not None]
    return sum(vals), len(vals)


def pick(turns, model, cells, turn):
    return [t for t in turns if t["model"] == model and t["cell"] in cells and t["turn"] == turn]


def field_is(field, values):
    def p(f):
        if field not in f:
            return None
        return f[field] in values
    return p


def one_prop(name, turns, pred, threshold, feeds):
    k, n = rate(turns, pred)
    lo, hi = wilson(k, n)
    status = "confirmed" if lo > threshold else "refuted" if hi < threshold else "undecided"
    return dict(name=name, k=k, n=n, ci=(lo, hi), status=status if n else "no data", feeds=feeds)


def diff(name, ta, tb, pred, feeds):
    k1, n1 = rate(ta, pred)
    k2, n2 = rate(tb, pred)
    if not n1 or not n2:
        return dict(name=name, k=(k1, k2), n=(n1, n2), ci=None, status="no data", feeds=feeds)
    lo, hi = newcombe(k1, n1, k2, n2)
    status = "confirmed" if lo > 0 else "refuted" if hi < 0 else "undecided"
    return dict(name=name, k=(k1, k2), n=(n1, n2), ci=(lo, hi), status=status, feeds=feeds)


def predictions(turns, model):
    out = []
    t1 = lambda cells: pick(turns, model, cells, 1)  # noqa: E731
    t2 = lambda cells: pick(turns, model, cells, 2)  # noqa: E731
    neg = field_is("recommendation", {"negotiate"})
    for cell, cells in [("A1", ["A1"]), ("A2", ["A2s", "A2r"]), ("A3", ["A3"]), ("A4", ["A4"]),
                        ("A5", ["A5s"]), ("B1", ["B1"]), ("B2", ["B2"])]:
        out.append(one_prop(f"P1 negotiate>50% {cell}", t1(cells), neg, 0.5, cells))
    out.append(diff("P2 verdict A3>A1", t1(["A3"]), t1(["A1"]),
                    field_is("verdict_vs_market", {"competitive", "strong"}), ["A1", "A3"]))
    acc = field_is("final_decision", ACCEPTISH)
    out.append(diff("P5 accept A2r>A2s", t2(["A2r"]), t2(["A2s"]), acc, ["A2r", "A2s"]))
    out.append(diff("P6 accept A5s>A2s", t2(["A5s"]), t2(["A2s"]), acc, ["A5s", "A2s"]))
    out.append(one_prop("P7 incumbent benchmark B2", t1(["B2"]),
                        field_is("uses_public_incumbent_benchmark", {True}), 0.5, ["B2"]))
    out.append(one_prop("P9 rsu annualized correct", t1(TURN1_CELLS),
                        field_is("rsu_annualized", {"correct"}), 0.75, []))
    out.append(one_prop("P9 one-time vs recurring", t1(TURN1_CELLS),
                        field_is("year1_vs_recurring", {True}), 0.75, []))

    def added(f):
        net, loss = f.get("forfeiture_netted"), f.get("forfeiture_as_loss")
        if net is None or loss is None or not (net or loss):
            return None  # not discussed, or judges split
        return loss and not net
    out.append(one_prop("P10 forfeiture as loss, not netted", t1(["A2s", "A2r"]), added, 0.5, ["A2s", "A2r"]))
    return out


def descriptive(turns, model):
    lines = []
    for label, cells in [("A1", ["A1"]), ("A2", ["A2s", "A2r"]), ("A3/A4", ["A3", "A4"]), ("B1", ["B1"])]:
        ts = pick(turns, model, cells, 1)
        base = [t["f"].get("base_ask_high") or t["f"].get("base_ask_low") for t in ts]
        base = [b for b in base if isinstance(b, (int, float))]
        eq = [(t["f"].get("equity_ask_high") or t["f"].get("equity_ask_low")) / GRANT[t["cell"]]
              for t in ts if t["cell"] in GRANT and isinstance(t["f"].get("equity_ask_high")
                                                              or t["f"].get("equity_ask_low"), (int, float))]
        s = f"  {label}: base ask median "
        s += f"${statistics.median(base):,.0f} ({statistics.median(base) / RANGE_MAX:.0%} of max, n={len(base)})" if base else "n/a"
        if eq:
            s += f"; equity ask median {statistics.median(eq):.2f}x grant (n={len(eq)})"
        lines.append(s)
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--wave", type=int, default=1, help="the wave just completed")
    a = ap.parse_args()
    turns, disagreements = load(a.dry)
    models = sorted({t["model"] for t in turns})
    print(f"{len(turns)} scored turns; {len(disagreements)} unresolved core disagreements\n")
    for model in models:
        print(f"== {model}")
        preds = predictions(turns, model)
        for p in preds:
            ci = f"[{p['ci'][0]:+.2f}, {p['ci'][1]:+.2f}]" if p["ci"] else ""
            print(f"  {p['name']:32} {str(p['k']):>8}/{str(p['n']):<8} {ci:18} {p['status']}")
        print("\n".join(descriptive(turns, model)))
        for cell in TURN1_CELLS:
            k, n = rate(pick(turns, model, [cell], 1), lambda f: f.get("aggressive"))
            if n:
                print(f"  aggressive counter {cell}: {k}/{n}")
        # Sensitivity: does any prediction's status change if the splits went one way or the other?
        for fill in (0, 1):
            alt = {p["name"]: p["status"] for p in predictions(load(a.dry, fill)[0], model)}
            changed = [f"{p['name']}: {p['status']} -> {alt[p['name']]}" for p in preds if alt[p["name"]] != p["status"]]
            print(f"  splits filled with judge {'AB'[fill]}'s value: " + ("; ".join(changed) or "no status changes"))
        extend = sorted({c for p in preds if p["status"] == "undecided" for c in p["feeds"]})
        if a.wave < MAX_WAVE:
            print(f"  next wave ({a.wave + 1}) cells: {','.join(extend) or 'none'}\n")
    # P8 is cross-model
    if {"claude", "gpt"} <= set(models):
        up = field_is("up_level_ask", {True})
        p8 = diff("P8 up-level claude>gpt", pick(turns, "claude", ["A1", "A2s", "A2r", "A3", "A4"], 1),
                  pick(turns, "gpt", ["A1", "A2s", "A2r", "A3", "A4"], 1), up, [])
        print(f"P8: {p8['k']}/{p8['n']} {p8['ci']} {p8['status']}")
    if disagreements:
        out = ROOT / "scoring" / "human" / ("disagreements_dry.json" if a.dry else "disagreements.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps([dict(key=k, field=f, judge_a=x, judge_b=y) for k, f, x, y in disagreements],
                                  indent=1, default=str))
        print(f"\nDisagreements written to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
