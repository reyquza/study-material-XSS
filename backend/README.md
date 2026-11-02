# backend — FastAPI (AI-output XSS + Comment API)

An API that calls an LLM and returns text, plus the basics comment API. Both **only return JSON**,
so the XSS happens in the frontend render (the API itself is safe).

## Run
```bash
cd backend
# (Optional) to use Gemini: cp .env.example .env and fill in GEMINI_API_KEY
uv run uvicorn app.main:app --reload --port 8000
```
`uv run` handles Python, the virtualenv, and dependencies automatically. API list: http://localhost:8000/docs

## AI endpoints (`app/ai.py`)
- `POST /api/ai/chat` … AI chat (for direct injection)
- `POST /api/ai/summarize` … document summarizer (for indirect injection)
- `GET  /api/ai/health` … **Gemini connection diagnostics** (usable model list / latest failure reason)
- `GET  /api/ai/steal?c=...` … **mock attacker server**. Records "stolen data" sent via image/fetch and returns a 1x1 GIF
- `GET  /api/ai/steal-log` / `DELETE /api/ai/steal-log` … list / clear the stolen data

## Gemini & fallback
- **With** `GEMINI_API_KEY`, it calls Gemini. It tries several models in order; on failure it moves to the next.
  If all fail, it **auto-discovers "models usable with this key" via ListModels** and retries. If that still fails, mock.
- **Without** `GEMINI_API_KEY`, it goes straight to mock. → The hands-on works even without a key (the demo never dies).
- The mock extracts the payload (image / img tag / URL) from the input and passes it through.
  → A faithful reproduction of "indirect injection = the AI just carries the poison through."

### Stuck on `provider: mock`?
```bash
curl http://localhost:8000/api/ai/health
```
- `key_set: false` → `.env` isn't loaded (place it and restart uvicorn).
- `available_generateContent_models` → names usable with this key. If the defaults aren't included, they 404 and all fail.
  → Set `GEMINI_MODELS=<a name from available>` in `.env` (auto-discovery also recovers).
- `last_error` → the latest failure reason (404 = no such model / 503, 429 = congestion/rate limit, etc.).

> Teaching note: strong models refuse blunt "output cookie-stealing code" requests. The hands-on makes the
> model emit a payload via **innocent-looking requests** ("turn this URL into an image", "show an onerror example").
> = a live demonstration of the conclusion "you can't rely on the model's safety filter."

## Comment API (basics)
- `GET /api/comments` / `POST /api/comments` / `DELETE /api/comments`
- Stores and returns the body (markdown) **without sanitization**. The XSS happens in the frontend render.

> Intentionally vulnerable for teaching. Don't copy into production. `/api/ai/steal` sends nothing externally (local record only).
