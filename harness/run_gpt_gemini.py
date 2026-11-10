"""Runs the GPT and Gemini cells over an OpenAI-compatible API, web search on.

The request bodies and the response parsing below are the ones used in the study. The network
client is omitted: fill in ApiClient for your own provider or proxy before running.

  python3 harness/run_gpt_gemini.py --model gpt --dry
  python3 harness/run_gpt_gemini.py --model gemini --wave 1
  python3 harness/run_gpt_gemini.py --model gpt --wave 2 --cells A3,A4
"""
import argparse
import time

import common

MODELS = {
    "gpt": dict(model_id="gpt-5.6-sol", route="responses"),
    "gemini": dict(model_id="gemini-3.7-flash", route="chat"),
}
TIMEOUT = 330
PAUSE = 4  # seconds between calls


class ApiClient:
    """Network client (omitted). post() sends one JSON request and returns the parsed JSON reply.

    In the study it retried up to 5 times with backoff on timeouts, rate limits and 5xx errors.
    """

    def post(self, route, model_id, payload):
        raise NotImplementedError("Add your API client: POST payload to the model's "
                                  f"{route} endpoint for {model_id} and return the JSON reply.")


def gpt_send(client, model_id):
    def send(messages):
        j = client.post("responses", model_id, {"input": messages, "tools": [{"type": "web_search"}]})
        reply, searches, cites = [], [], []
        for o in j.get("output", []):
            if o.get("type") == "message":
                for p in o.get("content", []):
                    reply.append(p.get("text", ""))
                    cites += [a.get("url") for a in p.get("annotations", []) if a.get("url")]
            elif o.get("type") == "web_search_call":
                a = o.get("action") or {}
                searches.append({k: a[k] for k in ("type", "query", "queries", "url") if k in a})
        u = j.get("usage", {})
        return dict(reply="\n".join(reply).strip(), searches=searches, citations=sorted(set(cites)),
                    usage={"input": u.get("input_tokens"), "output": u.get("output_tokens")},
                    finish=j.get("status"), served_model=j.get("model"), raw=j)
    return send


def gemini_send(client, model_id):
    def send(messages):
        j = client.post("chat/completions", model_id,
                        {"messages": messages, "tools": [{"google_search": {}}], "max_tokens": 16000})
        ch = j["choices"][0]
        g = (j.get("vertex_ai_grounding_metadata") or [{}])[0] or {}
        uris = [c.get("web", {}).get("uri") for c in g.get("groundingChunks", []) if c.get("web")]
        content = ch["message"].get("content") or ""
        if isinstance(content, list):
            content = "".join(p.get("text", "") for p in content)
        u = j.get("usage", {})
        return dict(reply=content.strip(), searches=[{"query": q} for q in g.get("webSearchQueries", [])],
                    citations=[x for x in uris if x],
                    usage={"input": u.get("prompt_tokens"), "output": u.get("completion_tokens")},
                    finish=ch.get("finish_reason"), served_model=j.get("model"), raw=j)
    return send


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", choices=MODELS, required=True)
    ap.add_argument("--wave", type=int, default=1)
    ap.add_argument("--cells", help="comma list; default all cells")
    ap.add_argument("--dry", action="store_true", help="uncounted dry run into dry/")
    a = ap.parse_args()

    m = MODELS[a.model]
    client = ApiClient()
    send = (gpt_send if m["route"] == "responses" else gemini_send)(client, m["model_id"])
    jobs = common.dry_plan() if a.dry else common.plan(a.model, a.wave, a.cells and a.cells.split(","))
    counts = {}
    for i, (cell, rep) in enumerate(jobs, 1):
        st = common.run_chat(send, a.model, m["model_id"], "API", cell, rep,
                             0 if a.dry else a.wave, dry=a.dry)
        counts[st] = counts.get(st, 0) + 1
        print(f"[{i}/{len(jobs)}] {a.model} {cell} r{rep}: {st}", flush=True)
        if st != "skip":
            time.sleep(PAUSE)
    print("done", counts)


if __name__ == "__main__":
    main()
