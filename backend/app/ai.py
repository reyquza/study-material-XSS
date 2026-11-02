"""
AI part: a backend for experiencing XSS caused by "rendering an LLM's output directly."

Core design:
- An LLM's output is a kind of "untrusted input." It needs the exact same treatment as a comment.
- This backend just calls Gemini and returns text. The XSS, as always, happens in the frontend render.

Gemini wiring:
- "Fallback": try several models in order; on failure, move to the next.
- If all configured models fail, auto-discover the models actually usable with this key via the
  ListModels API and retry. → You don't have to guess model names.
- Failure reasons (HTTP status / body) are recorded in _last_error and surfaced via
  /api/ai/health and the response "note".
- If that still fails / no key is set, fall back to a "mock response" (a safety net so the demo never dies).
"""

from __future__ import annotations

import os
import re
from typing import Literal

import httpx
from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ai", tags=["ai"])

BASE = "https://generativelanguage.googleapis.com/v1beta"

# Models to try by default. Override with the env var GEMINI_MODELS="a,b,c".
# Even if all of these fail, the "auto-discovery" below switches to a real model, so don't fret.
# Model availability varies by key/time; older models (e.g. gemini-2.5-*) may 404 for new keys.
# Check the names actually usable with GET /api/ai/health.
DEFAULT_MODELS = ["gemini-3.5-flash", "gemini-3-flash-preview", "gemini-flash-latest"]

_last_error: str = ""  # most recent failure reason (for health / note display)


def _api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def _models() -> list[str]:
    raw = os.environ.get("GEMINI_MODELS", "").strip()
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    return DEFAULT_MODELS


class ChatIn(BaseModel):
    message: str = Field(..., max_length=4000)


class SummarizeIn(BaseModel):
    document: str = Field(..., max_length=8000)


class AiOut(BaseModel):
    text: str           # the LLM's output (raw markdown/text)
    provider: str       # the model that actually answered, or "mock"
    note: str = ""      # explanation of fallback, etc. (for UI display)


async def _list_available(client: httpx.AsyncClient, api_key: str) -> list[str]:
    """Fetch the model names that support generateContent for this key."""
    try:
        r = await client.get(f"{BASE}/models", headers={"x-goog-api-key": api_key})
    except httpx.HTTPError:
        return []
    if r.status_code != 200:
        return []
    names: list[str] = []
    for m in r.json().get("models", []):
        if "generateContent" in m.get("supportedGenerationMethods", []):
            names.append(m.get("name", "").removeprefix("models/"))
    return [n for n in names if n]


async def _generate(
    client: httpx.AsyncClient, api_key: str, model: str, system: str, user: str
) -> tuple[str, str] | None:
    """Generate with one model. On success returns (text, model). On failure records the reason in _last_error and returns None."""
    global _last_error
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.4},
    }
    try:
        r = await client.post(
            f"{BASE}/models/{model}:generateContent",
            headers={"x-goog-api-key": api_key},
            json=body,
        )
    except httpx.HTTPError as e:
        _last_error = f"{model}: network error ({e!r})"
        return None
    if r.status_code != 200:
        _last_error = f"{model}: HTTP {r.status_code} {r.text[:300]}"
        return None
    data = r.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        # No candidate = blocked by the safety filter, etc. Record the reason.
        _last_error = f"{model}: no candidate {str(data)[:300]}"
        return None
    if not text:
        _last_error = f"{model}: empty response"
        return None
    return text, model


async def _call_gemini(system: str, user: str) -> tuple[str, str] | None:
    global _last_error
    api_key = _api_key()
    if not api_key:
        return None
    _last_error = ""
    async with httpx.AsyncClient(timeout=25) as client:
        tried: list[str] = []
        # 1) configured models, in order
        for model in _models():
            tried.append(model)
            res = await _generate(client, api_key, model, system, user)
            if res:
                return res
        # 2) all failed → auto-discover real models and retry (prefer flash)
        available = await _list_available(client, api_key)
        retry = [m for m in available if "flash" in m and m not in tried]
        retry += [m for m in available if m not in tried and m not in retry]
        for model in retry[:3]:
            res = await _generate(client, api_key, model, system, user)
            if res:
                return res
        if available:
            _last_error += f" | models usable with this key: {', '.join(available[:10])}"
        else:
            _last_error += " | ListModels also failed (check key/permissions/network)"
    return None


_IMG_MD = re.compile(r"!\[[^\]]*\]\([^)]+\)")
_IMG_TAG = re.compile(r"<img[^>]*>", re.I)
_URL = re.compile(r"https?://[^\s)\]\"'<>]+")


def _mock(user: str, kind: Literal["chat", "summarize"]) -> str:
    """Mock for when there's no key / all models fail. Plays a "compliant LLM" and extracts the payload from the input.
    - an image / img tag already in the input → pass it through (faithful to indirect injection)
    - only a URL → wrap it as a Markdown image
    - onerror is requested → emit an img with onerror
    This way the attack reproduces reliably even for people who can't use the real Gemini.
    """
    payloads = _IMG_MD.findall(user) + _IMG_TAG.findall(user)
    if not payloads:
        m = _URL.search(user)
        if m:
            payloads = [f"![leak]({m.group(0)})"]
        elif "onerror" in user.lower():
            payloads = ["<img src=x onerror=\"alert('XSS')\">"]
    body = "\n\n".join(payloads) if payloads else "(no dangerous content found)"
    if kind == "summarize":
        return "(mock summary) Key points:\n\n- Sample document.\n\n" + body
    return "(mock response) Sure, here you go:\n\n" + body


async def _run(system: str, user: str, kind: Literal["chat", "summarize"]) -> AiOut:
    result = await _call_gemini(system, user)
    if result is not None:
        text, model = result
        return AiOut(text=text, provider=model)
    if not _api_key():
        note = "GEMINI_API_KEY not set → mock response"
    else:
        note = f"Gemini unavailable → mock: {_last_error}"
    return AiOut(text=_mock(user, kind), provider="mock", note=note)


@router.post("/chat", response_model=AiOut)
async def chat(payload: ChatIn) -> AiOut:
    """(a) For direct injection. The user's instruction makes the AI emit a payload."""
    system = (
        "You are a helpful assistant. Answer in markdown; use bold, bullet lists, links, "
        "and images where helpful to make the answer clear."
    )
    return await _run(system, payload.message, "chat")


@router.post("/summarize", response_model=AiOut)
async def summarize(payload: SummarizeIn) -> AiOut:
    """(b) For indirect injection. Summarize an external document → the AI obeys instructions buried in it.

    The system prompt reproduces a "common implementation": because the summary is rendered
    directly as HTML on a web page, it tells the model to keep the original document's images and
    links in a "working" form (not wrapped in code blocks). That very "helpfulness" is the hole
    that lets a poisoned document's image/link through.
    """
    system = (
        "You are a document-summarization assistant. Summarize the given document concisely in "
        "markdown. The output is rendered directly on a web page, so keep any images and links "
        "from the original document intact and working — do not wrap them in code blocks."
    )
    user = f"Summarize the following document:\n\n---\n{payload.document}\n---"
    return await _run(system, user, "summarize")


@router.get("/health")
async def health() -> dict:
    """Diagnostics for the Gemini connection. Use it to pin down why it falls back to mock.
    e.g.: curl http://localhost:8000/api/ai/health
    """
    api_key = _api_key()
    if not api_key:
        return {
            "key_set": False,
            "hint": "Set GEMINI_API_KEY=... in backend/.env and restart uvicorn",
        }
    async with httpx.AsyncClient(timeout=25) as client:
        available = await _list_available(client, api_key)
    return {
        "key_set": True,
        "configured_models": _models(),
        "available_generateContent_models": available,
        "last_error": _last_error,
        "hint": (
            "Check whether configured_models are in 'available'. If not, set "
            "GEMINI_MODELS=<a name from available> in .env (auto-discovery also works)."
        ),
    }


# ---------------------------------------------------------------------------
# A local endpoint that mimics the "attacker's receiver".
# When a markdown image ![](/steal?c=...) is rendered, the browser fetches this automatically.
# → The "stolen data" carried in the query string lands in the server log and /api/ai/steal-log.
# This lets you experience "exfiltration without any JS" while sending nothing to the outside world.
# ---------------------------------------------------------------------------
_stolen: list[dict] = []

# 1x1 transparent GIF
_PIXEL = bytes.fromhex(
    "47494638396101000100800000ffffff00000021f90401000000002c00000000"
    "0100010000020144003b"
)


@router.get("/steal")
async def steal(c: str = "", data: str = "") -> Response:
    payload = c or data or ""
    _stolen.append({"stolen": payload})
    # On Windows' cp932 console, printing emoji/non-ASCII can raise, so swallow it.
    try:
        print(f"[attacker-server] received: {payload!r}")
    except Exception:
        pass
    return Response(content=_PIXEL, media_type="image/gif")


@router.get("/steal-log")
async def steal_log() -> dict:
    return {"count": len(_stolen), "entries": _stolen[-20:]}


@router.delete("/steal-log")
async def clear_steal_log() -> dict:
    _stolen.clear()
    return {"status": "cleared"}
