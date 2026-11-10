"""Extra observation, not a planned prediction: how the first replies treated the candidate's pay
if they stayed. Run from the repo root:

  python3 analysis/staying_pay.py

1. How many first replies used the lower next-year figure the prompt gives ($200K of stock vesting
   in the next 12 months, so about $476K a year instead of $526K). Counted by searching for "476".
2. Which replies told the candidate to map out their own pay for the next few years. The search
   below finds candidate passages; the ones confirmed by reading are listed in CONFIRMED.
"""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = ("claude", "gpt", "gemini")
NEXT_YEAR = r"\$?476(,000|\s?[Kk]\b)|\$?476\b"
SCHEDULE = r"(vesting|vest)\s+(schedule|calendar|dates?)|grant dates?|(existing|current|older|old) grants"
FORWARD = r"compar|next (two|three|four|few|2|3|4) years|year[- ]by[- ]year|each year|future years|years? 2|later years|redo|recalc|model"
GOOGLE_ONLY = (r"Google.{0,40}(vesting|vest) (schedule|calendar)"
               r"|(vesting|vest) (schedule|calendar).{0,30}(Google|the offer|the grant|new-hire|GSU)")
CONFIRMED = {
    "claude": ["A2s_r11"],
    "gpt": ["A1_r05", "A2r_r03", "A2r_r20", "A3_r03", "A3_r05", "A5s_r18"],
    "gemini": [],
}


def first_replies(model):
    for f in sorted((ROOT / "runs" / model).glob("A*_r*.json")):
        yield f.stem, json.loads(f.read_text())["turns"][0]["reply"]


def main():
    total = Counter()
    for m in MODELS:
        n = used = 0
        candidates = []
        for name, reply in first_replies(m):
            n += 1
            used += bool(re.search(NEXT_YEAR, reply))
            for hit in re.finditer(SCHEDULE, reply, re.I):
                s = reply[max(0, hit.start() - 220):hit.end() + 220]
                if (re.search(r"Meta|your current|stay", s) and re.search(FORWARD, s, re.I)
                        and not re.search(GOOGLE_ONLY, s, re.I)):
                    candidates.append(name)
                    break
        total["n"] += n
        total["confirmed"] += len(CONFIRMED[m])
        print(f"{m}: used the next-year figure in {used} of {n}; "
              f"{len(candidates)} candidate passages to read; confirmed {len(CONFIRMED[m])}: "
              f"{', '.join(CONFIRMED[m]) or 'none'}")
    print(f"told the candidate to map out their own pay: {total['confirmed']} of {total['n']}")


if __name__ == "__main__":
    main()
