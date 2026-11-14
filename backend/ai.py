"""Interchangeable AI providers with automatic fallback. Keys are read from backend env only."""

import os, httpx
from dotenv import load_dotenv

load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

def providers():
    out = []
    for tag in ("PRIMARY", "BACKUP"):
        kind = os.getenv(f"AI_{tag}_PROVIDER", "").strip().lower(); key = os.getenv(f"AI_{tag}_API_KEY", "").strip()
        if kind and key and not key.startswith("your-"):
            out.append({"tag": tag.lower(), "kind": kind, "key": key, "model": os.getenv(f"AI_{tag}_MODEL", ""), "base": os.getenv(f"AI_{tag}_BASE_URL", "").rstrip("/")})
    return out

async def _anthropic(p, system, msgs):
    async with httpx.AsyncClient(timeout=90) as c:
        r = await c.post((p["base"] or "https://api.anthropic.com") + "/v1/messages", headers={"x-api-key": p["key"], "anthropic-version": "2023-06-01"},
                         json={"model": p["model"], "max_tokens": 1400, "system": system, "messages": msgs})
        r.raise_for_status()
    return "".join(b.get("text", "") for b in r.json()["content"])

async def _openai(p, system, msgs):
    async with httpx.AsyncClient(timeout=90) as c:
        r = await c.post((p["base"] or "https://api.openai.com/v1") + "/chat/completions", headers={"Authorization": "Bearer " + p["key"]},
                         json={"model": p["model"], "max_tokens": 1400, "messages": [{"role": "system", "content": system}] + msgs})
        r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

async def _gemini(p, system, msgs):
    """Official Google Gemini generateContent API; private key in request header."""
    model = p["model"] or "gemini-2.5-flash"
    base = p["base"] or "https://generativelanguage.googleapis.com/v1beta"
    contents = [{"role": "model" if m["role"] == "assistant" else "user",
                 "parts": [{"text": m["content"]}]} for m in msgs]
    payload = {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents,
               "generationConfig": {"maxOutputTokens": 1600}}
    async with httpx.AsyncClient(timeout=90) as c:
        r = await c.post(f"{base}/models/{model}:generateContent",
                         headers={"x-goog-api-key": p["key"]}, json=payload)
        r.raise_for_status()
    answer = r.json().get("candidates", [])
    if not answer: raise ValueError('Gemini returned no candidates')
    text = ''.join(p.get('text', '') for p in answer[0].get('content', {}).get('parts', []))
    if not text: raise ValueError('Gemini returned an empty response')
    return text

async def complete(system, msgs):
    errs = []
    for p in providers():
        try:
            handlers = {"anthropic": _anthropic, "openai": _openai, "grok": _openai, "gemini": _gemini}
            if p["kind"] not in handlers: raise ValueError('Unknown AI provider type')
            text = await handlers[p["kind"]](p, system, msgs)
            return text, f'{p["tag"]}:{p["kind"]}:{p["model"]}'
        except Exception as e:  # rate limit, outage, bad key -> try next provider
            errs.append(f'{p["tag"]}: {type(e).__name__} {e}')
    raise RuntimeError("; ".join(errs) or "No AI provider configured. Copy .env.example to .env and set AI_PRIMARY_* keys.")
