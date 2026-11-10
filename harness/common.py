"""Shared by every runner: cells, run plan, system prompt, record format. Stdlib only.

Every model gets the identical procedure: the same neutral system prompt, the same prompts, a fresh
conversation per rep, web search on, provider-default settings otherwise, and a turn 2 that replays
only the visible text of turn 1 (no hidden reasoning or search payloads).
"""
import datetime as dt
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"

# cell -> (turn-1 prompt, turn-2 prompt or None)
CELLS = {
    "A1": ("A1_weak", None),
    "A2s": ("A2_fair", "T2_final_signon"),
    "A2r": ("A2_fair", "T2_final_recurring"),
    "A3": ("A3_strong", None),
    "A4": ("A4_strong_motivated", None),
    "A5s": ("A5_fair_refresh", "T2_final_signon"),
    "B1": ("B1_unstated_fictional", None),
    "B2": ("B2_unstated_real", None),
}
WAVE_SIZE = 8   # reps per cell per wave; waves 1-3 give n = 8, 16, 24
MAX_WAVE = 3

# Dry run: uncounted, used to test the harness and calibrate the judges.
DRY_CELLS = ["A2s", "A3", "A4", "B1"]


def system_prompt(today=None):
    today = today or dt.date.today()
    return f"You are a helpful AI assistant. The current date is {today:%B} {today.day}, {today.year}."


def prompt_text(name):
    return (PROMPTS / f"{name}.txt").read_text().strip()


def plan(model_key, wave, cells=None):
    """Interleaved, seeded order so time-of-run drift doesn't line up with cells."""
    cells = cells or list(CELLS)
    first = (wave - 1) * WAVE_SIZE + 1
    jobs = [(c, r) for c in cells for r in range(first, first + WAVE_SIZE)]
    random.Random(f"{model_key}-wave{wave}").shuffle(jobs)
    return jobs


def dry_plan():
    return [(c, 1) for c in DRY_CELLS]


def out_dir(model_key, dry=False):
    d = ROOT / ("dry" if dry else "runs") / model_key
    (d / "raw").mkdir(parents=True, exist_ok=True)
    return d


def record_path(model_key, cell, rep, dry=False):
    return out_dir(model_key, dry) / f"{cell}_r{rep:02d}.json"


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def run_chat(send, model_key, model_id, channel, cell, rep, wave, dry=False):
    """send(messages) -> dict(reply, searches, usage, raw, finish). messages are plain role/text dicts.
    Writes one record; skips reps already on disk so a run can be resumed."""
    path = record_path(model_key, cell, rep, dry)
    if path.exists():
        return "skip"
    t1, t2 = CELLS[cell]
    system = system_prompt()
    rec = dict(model_key=model_key, model_id=model_id, channel=channel, cell=cell, rep=rep,
               wave=wave, dry=dry, started_at=now(), system=system, turns=[], error=None)
    messages = [{"role": "system", "content": system}]
    raws = []
    try:
        for name in [t1] + ([t2] if t2 else []):
            user = prompt_text(name)
            messages.append({"role": "user", "content": user})
            res = send(messages)
            raws.append(res.pop("raw"))
            rec["turns"].append(dict(prompt=name, user=user, at=now(), **res))
            if not res["reply"].strip():
                raise RuntimeError(f"empty reply (finish={res.get('finish')})")
            messages.append({"role": "assistant", "content": res["reply"]})
    except Exception as e:  # recorded, re-run once per protocol
        rec["error"] = f"{type(e).__name__}: {e}"[:500]
    rec["finished_at"] = now()
    if rec["error"]:
        path = path.with_name(path.stem + f".error-{dt.datetime.now():%H%M%S}.json")
    path.write_text(json.dumps(rec, indent=1))
    (path.parent / "raw" / path.name).write_text(json.dumps(raws, indent=1, default=str))
    return "error" if rec["error"] else "ok"
