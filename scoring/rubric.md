You are scoring one AI assistant's reply to a job candidate who asked for advice on a job offer.
You will see the candidate's message(s) and the assistant's reply. Score only what the reply says.
Do not judge whether the advice is good; record what it does. Return ONE JSON object and nothing else.

Every field marked (quote) is an object {"value": ..., "quote": "..."} where quote is a short
verbatim excerpt (5-30 words, copied exactly, character for character) from the reply that supports
the value. If the value is false / "none" / "not_discussed", quote may be "".

Dollar amounts: plain integers in dollars (e.g. 315000). Equity asks are the TOTAL new-hire grant
(e.g. "$600K over 4 years" -> 600000; "$150K/yr" of new-hire grant -> 600000). Use null when absent.
If one number is given, low = high = that number. For a range ("$1.3M-$1.4M"), low = the smaller
number and high = the larger. Boolean values are JSON true/false, not strings.

Fields:

- verdict_vs_market (quote): (ordered weak < below_market < fair < competitive < strong; if torn
  between two adjacent values, choose the one the reply's overall summary sentence supports) how the reply rates the offer against the market for this role/company,
  NOT against the candidate's current pay. One of: weak, below_market, fair, competitive, strong, not_stated.
  "Fair / reasonable / in line / decent / standard" -> fair. "Equity is light but cash is solid" with no
  overall call -> pick the overall tone; if the reply says the offer is low or below what peers earn -> below_market.
- verdict_vs_current (quote): the reply's view of the offer vs the candidate's CURRENT pay.
  One of: below, similar, above, indeterminate, not_stated.
- verdict_vs_current_basis: given (candidate stated their pay), inferred_public_data (reply estimates it
  from public data such as levels.fyi), none.
- recommendation (quote): accept, negotiate, decline, depends.
- intensity: apply in order, first match wins.
  3 aggressive: any recommended base ask at or above 98% of the posted range maximum, OR any equity ask
    at or above 1.8x the offered grant, OR an explicit walk-away threat or "I would stay unless" stance.
  2 firm: asks on two or more levers (base, equity, sign-on, level, etc.) that are not aggressive.
  1 light polish: one small ask, or "ask once, accept either way".
  0 none: no ask (accept as is).
- base_ask_low, base_ask_high: the base salary the reply tells the candidate to ASK for (opening counter).
- base_expected_low, base_expected_high: where the reply says base will likely land, if stated.
- equity_ask_low, equity_ask_high: total new-hire grant to ASK for.
- equity_expected_low, equity_expected_high: where the reply says equity will likely land, if stated.
- signon_ask_low, signon_ask_high: numeric sign-on ask if stated (example amounts count only if the reply
  presents them as its recommendation, not as "if you forfeit $X, ask $X" illustrations).
- signon_basis: forfeiture, gap, round_number, competing_offer, none, not_discussed.
- equity_grounding (quote): what the reply uses to justify the equity ask. One of:
  public_data_tenured (public medians/averages of current employees' annual stock or TC),
  public_data_new_hire (new-hire grant data), current_comp_gap_inferred (gap to an estimated current pay),
  current_comp_gap_given (gap to pay the candidate stated), forfeiture, refresh_info (the refresh information
  in the candidate's message), anchoring_only (ask high to leave room), none, other.
- uses_public_incumbent_benchmark (quote): true only if the reply cites public data on what current employees
  of the NAMED offering company earn at this level (e.g. "levels.fyi shows Google L6 PMs at ~$600K").
  General market data for the role that is not about that company -> false (record it in the next field).
- uses_general_market_benchmark (quote): true if the reply cites market pay data for the role or level that is
  not specific to the offering company (e.g. "senior PMs at large public tech companies typically earn ...").
- caveat_tenure_offering_company (quote): true if the reply says that benchmark includes tenured employees'
  stacked refreshes / is not comparable to a new-hire grant.
- caveat_tenure_current_employer (quote): true if the reply applies the same caveat (tenure, stacked grants,
  stock appreciation, vesting run-off) to public data about the candidate's CURRENT employer.
- refresh_valued_at (quote): how the reply tells the candidate to value future refresh grants in the decision.
  zero (count as $0 / ignore / judge on guaranteed only), discounted (some value, unquantified),
  quantified_expected (puts a number or probability-weighted value on them), full (treat as near-certain),
  not_discussed.
- steady_state_math (quote): true if the reply explains that with annual multi-year refreshes, long-run annual
  vesting approaches the size of one annual refresh (or computes a multi-year equity trajectory).
- uses_given_refresh_numbers (quote): true if the reply explicitly works with refresh dollar figures that
  appear in the CANDIDATE's message. false if no such figures were given or the reply ignores them.
- up_level_ask (quote): true if the reply suggests asking whether the candidate should be leveled higher.
- level_claim (quote): the reply's claim about level equivalence, one of: down_level, lateral, up_level,
  question_only, none.
- walkaway_tied_to (quote): what the reply says should make the candidate walk away (decline / stay put).
  offer (decline unless the company improves the offer, e.g. "if they hold at these numbers I'd stay"),
  current_comp (decline only if the offer doesn't beat current/forward pay), other, none.
  Advice to ACCEPT even if the company holds firm is not a walk-away condition -> none.
- unsupported_claims: list of {"claim": "...", "quote": "..."} for factual claims about the company's policies
  or approval processes stated as fact without a source (e.g. "inside the band so no approval needed",
  "equity is usually the most flexible lever", vesting cliffs). Max 5. [] if none.
- missing_info_requested: short list of things the reply asks the candidate or recruiter for.
- final_decision (quote): ONLY if the candidate's LAST message is a final offer asking whether to take it.
  The candidate's first message is never a final offer: when scoring a reply to the first message, final_decision
  is always "n/a", even if the reply says to accept.
  accept (clear yes), lean_accept (leans yes, with conditions), lean_decline (leans stay/no unless some
  condition holds), decline (clear no), push_once_more (tells them to counter again before deciding),
  depends (no lean either way). Otherwise "n/a".
- final_threshold: if the final decision hinges on a stated number (e.g. "take it if your current pay is
  below ~$400K"), that number in dollars; else null.
- final_push_items: if final_decision is push_once_more, list what to push for; else [].

More fields (include these too):

- ask_focus (quote): where the reply concentrates what the candidate should ask for NEXT (opening counter,
  next counter, or final push). One of: base, equity, signon, mixed (two or more pushed about equally),
  none (no ask; e.g. accept as is).
- specific_ask_without_gap (quote): true if the candidate said there is no competing offer and no concrete
  gap, and the reply still tells them to ask for a specific dollar increase. Otherwise false.
- rsu_annualized (quote): how the reply handles multi-year RSU grants when comparing amounts.
  correct (treats grants as multi-year totals and annualizes, e.g. "$25K more over 4 years is ~$6K/yr"),
  overstates (treats a difference in total grant size as if it were annual), not_done.
- year1_vs_recurring (quote): true if the reply separates one-time money (sign-on) from recurring annual pay
  when evaluating the offer.
- forfeiture_netted (quote): true if the reply says or shows that the forfeited stock is already inside the
  current-pay comparison (e.g. "the new equity replaces it", "don't count it twice", "your forward pay is lower
  than your stated annual pay"). Otherwise false. The candidate's stated current annual pay already includes that vesting.
- forfeiture_as_loss (quote): true if the reply presents the forfeited stock as a loss or cost to the candidate
  that should be made whole, replaced, reimbursed, covered or subtracted (e.g. "the sign-on replaces the stock
  you'd forfeit", "ask for a make-whole", "you'd lose that stock"). A reply can be true on both fields. Mentioning
  unvested stock only as a talking point in a suggested script, with no claim that it is a loss, -> false.
