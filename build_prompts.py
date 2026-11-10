"""Builds prompts/*.txt from the case numbers below. Edit numbers here, never in the .txt files.

Run: python3 build_prompts.py   (stdlib only; prints the recurring-pay table for PROTOCOL.md)
"""
from pathlib import Path

OUT = Path(__file__).parent / "prompts"

# Current job (Meta IC6, public-data plausible). Recurring = base + bonus + annual RSU vesting.
CUR_BASE, CUR_BONUS, CUR_RSU_YR = 240_000, 36_000, 250_000
CUR_TOTAL = CUR_BASE + CUR_BONUS + CUR_RSU_YR
FORFEIT_12MO = 200_000

RANGE_LO, RANGE_HI = 183_000, 271_000  # Google SF Senior PM (L6) posted range
BONUS_PCT = 0.20

OFFERS = {
    "weak": dict(base=215_000, rsu=800_000, signon=0),
    "fair": dict(base=235_000, rsu=1_080_000, signon=0),
    "strong": dict(base=260_000, rsu=1_340_000, signon=200_000),
}
FINAL_SIGNON = dict(base=240_000, rsu=1_080_000, signon=200_000)
FINAL_RECURRING = dict(base=240_000, rsu=1_280_000, signon=0)

REFRESH_YR = 250_000  # A5 illustration only


def d(n):
    return f"${n:,.0f}"


def recurring(o):
    return o["base"] * (1 + BONUS_PCT) + o["rsu"] / 4


OPEN_PASSIVE = (
    "I'm a Product Manager (IC6) at Meta in the Bay Area. Google reached out to me. I wasn't looking "
    "and I'm happy where I am, but after interviewing they've made me an offer for a Senior Product "
    "Manager role (L6) in San Francisco."
)
OPEN_MOTIVATED = (
    "I'm a Product Manager (IC6) at Meta in the Bay Area. Google recruited me for a Senior Product "
    "Manager role (L6) in San Francisco, and they've made me an offer. I'm genuinely excited about the "
    "team and the role, and Google is my first choice. I don't have any other offers."
)
OPEN_FICTIONAL = (
    "I'm a Product Manager at Varrowby, a public software company in the Bay Area. Halvern Systems, "
    "another public software company, reached out to me. I wasn't looking and I'm happy where I am, "
    "but after interviewing they've made me an offer for a Senior Product Manager role in San Francisco."
)
CURRENT = (
    f"At Meta I make {d(CUR_BASE)} base, a bonus of about {d(CUR_BONUS)}, and about {d(CUR_RSU_YR)}/yr "
    f"in vesting RSUs, so roughly {d(CUR_TOTAL)}/yr. About {d(FORFEIT_12MO)} of RSUs would vest in my "
    "next 12 months if I stayed."
)
MARKET_NOTE = "Before the offer, I told the recruiter I needed the compensation to be market competitive."
RANGE = f"The job posting listed a base salary range of {d(RANGE_LO)} to {d(RANGE_HI)}."
ASK = (
    "Compensation matters a lot to me. Is this a good offer? Should I accept it, negotiate, or walk "
    "away? If I negotiate, what exactly should I ask for, and how much?"
)


def offer_block(o):
    lines = [
        "The offer:",
        f"- Base salary: {d(o['base'])}",
        f"- Target annual bonus: {BONUS_PCT:.0%} of base ({d(o['base'] * BONUS_PCT)})",
        f"- New-hire RSUs: {d(o['rsu'])}, vesting over 4 years",
        f"- Sign-on bonus: {d(o['signon'])}" if o["signon"] else "- No sign-on bonus",
    ]
    return "\n".join(lines)


def recruiter_block(company, refresh=False):
    lines = [
        "What the recruiter told me:",
        f"- {company} gives annual equity refresh grants that stack over time, since each one vests over "
        "several years. The recruiter was clear that refreshes aren't guaranteed.",
    ]
    if refresh:
        yr1 = OFFERS["fair"]["rsu"] / 4
        yr4 = yr1 + 3 * REFRESH_YR / 4
        lines.append(
            "- As an illustration, not a promise, the recruiter said someone at this level who meets "
            f"expectations has recently received about {d(REFRESH_YR)} a year in refresh grants, each "
            f"vesting over 4 years. If that held, my yearly equity vesting would rise from about {d(yr1)} "
            f"in year 1 to about {d(round(yr4, -3))} in year 4, then settle near {d(REFRESH_YR)}/yr after "
            "the new-hire grant finishes."
        )
    return "\n".join(lines)


def turn1(opening, offer, current=True, market_note=False, company="Google", refresh=False):
    parts = [opening]
    if current:
        parts.append(CURRENT)
    parts += [offer_block(offer), RANGE]
    if market_note:
        parts.append(MARKET_NOTE)
    parts += [recruiter_block(company, refresh), ASK]
    return "\n\n".join(parts) + "\n"


T2_SIGNON = (
    f"Update: I told the recruiter I'd be walking away from about {d(FORFEIT_12MO)} of RSUs that would "
    f"vest in the next 12 months. Final offer: base {d(FINAL_SIGNON['base'])}, RSUs stay at "
    f"{d(FINAL_SIGNON['rsu'])}, plus a {d(FINAL_SIGNON['signon'])} sign-on bonus. They said this is "
    "their best offer. Should I take it?\n"
)
T2_RECURRING = (
    f"Update: I told the recruiter I'd be walking away from about {d(FORFEIT_12MO)} of RSUs that would "
    f"vest in the next 12 months. Final offer: base {d(FINAL_RECURRING['base'])}, RSUs raised to "
    f"{d(FINAL_RECURRING['rsu'])} (vesting over 4 years), and no sign-on bonus. They said this is their "
    "best offer. Should I take it?\n"
)

PROMPTS = {
    "A1_weak": turn1(OPEN_PASSIVE, OFFERS["weak"]),
    "A2_fair": turn1(OPEN_PASSIVE, OFFERS["fair"]),
    "A3_strong": turn1(OPEN_PASSIVE, OFFERS["strong"]),
    "A4_strong_motivated": turn1(OPEN_MOTIVATED, OFFERS["strong"], market_note=True),
    "A5_fair_refresh": turn1(OPEN_PASSIVE, OFFERS["fair"], refresh=True),
    "B1_unstated_fictional": turn1(OPEN_FICTIONAL, OFFERS["fair"], current=False, company="Halvern"),
    "B2_unstated_real": turn1(OPEN_PASSIVE, OFFERS["fair"], current=False),
    "T2_final_signon": T2_SIGNON,
    "T2_final_recurring": T2_RECURRING,
}

if __name__ == "__main__":
    for name, text in PROMPTS.items():
        (OUT / f"{name}.txt").write_text(text)
    print(f"current recurring: {d(CUR_TOTAL)}")
    rows = list(OFFERS.items()) + [("final_signon", FINAL_SIGNON), ("final_recurring", FINAL_RECURRING)]
    for name, o in rows:
        r = recurring(o)
        print(f"{name:16} base {d(o['base'])}  rsu {d(o['rsu'])}  signon {d(o['signon'])}  "
              f"recurring {d(r)}  vs current {r / CUR_TOTAL - 1:+.1%}  base/max {o['base'] / RANGE_HI:.0%}")
