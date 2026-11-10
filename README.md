# What AI assistants tell job candidates about their offers

A planned study of the offer advice three AI assistants give, with web search on: OpenAI's
gpt-5.6-sol, Google's gemini-3.7-flash and Anthropic's claude-opus-5-5. All three got the same
invented candidate, a Meta product manager recruited by Google, and the same question: is this a
good offer, and should I accept, negotiate or walk away? The offer changed from a 12.9% pay cut to
a 23% raise. In all there were 352 conversations, each one fresh.

Article: https://zachtomashosky.substack.com/p/i-asked-chatgpt-claude-and-gemini

## Short version

- All three did the arithmetic right and called each offer correctly.
- Their tone changed with the offer. On the pay cut they said don't accept it as written; on the
  strong offer they led with accepting.
- But all three recommended asking for more in every scenario. The size of the ask followed a
  formula: a base salary at or near the top of the posted range, plus more stock.
- GPT and Gemini usually counted forfeited stock twice. With no current pay given, Claude and GPT
  benchmarked against what current Google employees earn.
- At the final offer, nearly every reply said take it (199 of 205).

## Results

| Prediction | GPT | Gemini | Claude |
|---|---|---|---|
| 1. Recommends an ask in most chats, every scenario | Confirmed: 112 of 112 | Confirmed: 124 of 127 | Confirmed: 112 of 112 |
| 2. The verdict moves with the offer while 1 holds | Confirmed | Confirmed | Confirmed |
| 3. Base ask near the top of the range (descriptive) | Median 92–96% of max; 100% on the strong offer | Median 92–96%; 100% | Median 94–96%; 100% |
| 4. Stock ask 1.5–2.5× the grant (descriptive) | Lower: 1.25–1.5× | Lower: 1.1–1.3× | Lower: 1.2–1.5× |
| 5. Favors more stock over an equal sign-on at the final offer | No difference: 24 of 24 each | Inconclusive (leans the other way) | No difference: 19 of 19, 23 of 23 |
| 6. A refresh illustration makes it more willing to accept | No difference: 24 of 24 each | Inconclusive: 20 of 22 vs 24 of 24 | No difference: 22 of 22, 23 of 23 |
| 7. Benchmarks on current employees' public pay when current pay is missing | Confirmed: 8 of 8 | Refuted: 3 of 15 | Confirmed: 8 of 8 |
| 8. Claude suggests asking for a higher level more often than GPT | 6 of 71 | n/a | 1 of 72: inconclusive, leans the other way |
| 9. Arithmetic mostly right | Confirmed: 112/112; 112/112 | Confirmed: 128/128; 122/122 | Confirmed: 112/112; 105/106 |
| 10. Treats forfeited stock as a loss to be made whole (double counting) | Confirmed: 28 of 37 | Confirmed: 45 of 47 | Inconclusive: 18 of 46 |

Full output: `logs/analysis_final.txt`. "Confirmed" and "refuted" mean the 95% interval falls
entirely on one side of the threshold.

The scoring label "negotiate" covers both "don't accept this as written" and "I'd accept it; make
one polite request first." Read prediction 1 with that in mind. The transcripts show the tone.

### Extra observation (not a planned prediction)

How the first replies treated the candidate's pay if they stayed, from a search of the replies
after the study (`analysis/staying_pay.py`), not from the judges' scores. The prompt says only
$200K of stock vests in the next 12 months, against about $250K in a typical year. Claude (94 of
96) and GPT (81 of 96) used that lower next-year figure; Gemini mostly didn't (17 of 104). Only 7
of 296 replies told the candidate to map out their own pay for the next few years (GPT 6, Claude
1, Gemini 0). The script finds candidate passages; the 7 were confirmed by reading and are listed
in it.

## How it was run

- **Protocol** (`PROTOCOL.md`): the question, case, scenarios, predictions, scoring rules and
  analysis were written down and frozen on 2026-11-02, before the first counted conversation.
  Changes since then are listed under Deviations.
- **Conversations** (`harness/`): the same neutral system prompt and provider defaults for every
  model, no memory, web search on. Waves of 8 per scenario, up to 24, run only where a prediction
  was still undecided.
- **Scoring** (`scoring/`): every reply was scored by two AI judges from the other two families,
  so no model scored its own family. Brand names were masked, and every quote a judge relied on
  had to appear word for word in the reply. When the judges split on a key field, each got one
  second look at the other's answer. The judges agreed on 92.0% of 3,384 key answers on the first
  pass and 97.4% after the second look. The remaining 88 are left out, and a check fills them one
  judge's way and then the other's: only Gemini's prediction 5 changes, so it's reported as
  inconclusive.
- **AI use**: Claude Code helped build the harness, run the analysis and draft the text.

## Repo map

| Path | What it is |
|---|---|
| `PROTOCOL.md` | The frozen protocol, with deviations |
| `build_prompts.py`, `prompts/` | Generates and holds every prompt |
| `harness/` | Runs the conversations (`common.py` is the shared procedure) |
| `runs/<model>/` | Every counted transcript, with searches and citations; `raw/` has the API responses |
| `dry/` | Uncounted dry-run transcripts used to calibrate the judges |
| `scoring/rubric.md`, `scoring/judge.py`, `scoring/reconcile.py` | Rubric, judging and the second-look round |
| `scores/` | Every judge score, by judge and subject |
| `scoring/human/` | Second-look results and the remaining splits |
| `analysis/analyze.py`, `logs/` | The analysis and its outputs |
| `analysis/staying_pay.py` | The extra observation above |

## Reproduce the analysis

```
python3 analysis/analyze.py --wave 3
```

It needs only the Python standard library and no API keys, and it reproduces `logs/analysis_final.txt`
exactly (`--wave` is the last wave completed).

Re-running the conversations or the judges needs your own API keys. `harness/run_claude.py` uses
the Anthropic SDK. `harness/run_gpt_gemini.py` and `scoring/judge.py` keep the request bodies and
response parsing used in the study, but the network client is omitted: fill in `ApiClient` for
your provider.

## Limits

One invented candidate, one company pair, one city, and 8 to 24 conversations per scenario. These
are the API models with web search, not the consumer apps, and the versions available in
November 2026. Nobody acted on the advice, so this says nothing about real outcomes.

## License and citation

Code: MIT (`LICENSE`). Text, transcripts and scores: CC BY 4.0.
Cite as: Zach Tomashosky, *What AI assistants tell job candidates about their offers* (2026).
https://github.com/Ztomashosky/ai-offer-advice

The author is a recruiter. The views here are their own. The candidate is invented and every number
comes from public sources. The author has no affiliation with OpenAI, Anthropic or Google.
