"""Interchangeable AI providers. Fast-fail demo mode, bounded exact-request cache.

Keys are read from backend env only. Cache is per process, not durable; never
serve a response for a different prompt, farm, field or conversation.
"""
import asyncio
import hashlib
import json
import time
from collections import OrderedDict

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
    async with httpx.AsyncClient(timeout=_request_timeout()) as c:
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

# Exact-input cache: repeated presentation questions return without another API call.
# A per-process cache is intentionally small and cleared on service restart.
_CACHE = OrderedDict()
_CACHE_LIMIT = 128
_CACHE_TTL = 3600


def _request_timeout():
    try:
        return max(3.0, min(45.0, float(os.getenv("AI_REQUEST_TIMEOUT_SECONDS", "9"))))
    except ValueError:
        return 9.0


def _cache_key(system, msgs, configured):
    # Include model/provider configuration so a model change invalidates prior answers.
    # Hash secrets instead of storing them in plain text as cache keys.
    configuration = [(p["kind"], p["model"], p["base"], hashlib.sha256(p["key"].encode()).hexdigest()) for p in configured]
    body = json.dumps([system, msgs, configuration], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


async def complete(system, msgs):
    configured = providers()
    if not configured:
        raise RuntimeError("No AI provider configured. Set AI_PRIMARY_PROVIDER and AI_PRIMARY_API_KEY.")
    key = _cache_key(system, msgs, configured)
    cached = _CACHE.get(key)
    if cached:
        answer, provider, created = cached
        if time.monotonic() - created < _CACHE_TTL:
            _CACHE.move_to_end(key)
            return answer, provider + ":cached"
        del _CACHE[key]
    errors = []
    handlers = {"anthropic": _anthropic, "openai": _openai, "grok": _openai, "gemini": _gemini}
    # No slow retry loop: presentation mode prioritizes a bounded response time.
    for p in configured:
        try:
            if p["kind"] not in handlers:
                raise ValueError("Unknown AI provider type")
            answer = await asyncio.wait_for(
                handlers[p["kind"]](p, system, msgs), timeout=_request_timeout() + 1
            )
            provider = f'{p["tag"]}:{p["kind"]}:{p["model"]}'
            _CACHE[key] = (answer, provider, time.monotonic())
            _CACHE.move_to_end(key)
            while len(_CACHE) > _CACHE_LIMIT:
                _CACHE.popitem(last=False)
            return answer, provider
        except (httpx.HTTPError, asyncio.TimeoutError, ValueError) as exc:
            if isinstance(exc, httpx.HTTPStatusError):
                code = exc.response.status_code
                errors.append(f'{p["tag"]}: Google/provider HTTP {code}')
            elif isinstance(exc, (httpx.TimeoutException, asyncio.TimeoutError)):
                errors.append(f'{p["tag"]}: timed out')
            else:
                errors.append(f'{p["tag"]}: {type(exc).__name__}')
    raise RuntimeError("; ".join(errors) + ". Try a configured backup provider or use a previously prepared answer.")
