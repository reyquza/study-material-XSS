# Introduction to XSS
## ~ Modern XSS Hands-on Training Material ~

Run an **intentionally vulnerable AI app** on your own machine and experience the
**XSS / data exfiltration** that happens when you **render an LLM's output on screen** —
in an "attack → defend" flow.

> ⚠️ **Important**: This code is *intentionally vulnerable for learning*. **Do not copy it into production.**
> Only practice attacks **on your own local environment**. Nothing is ever sent to the outside world
> (`/api/ai/steal` is a local mock attacker server).

---

## Learning Objectives

| Stage | Theme | In one line |
|---|---|---|
| Basics | What XSS is | Input that should be "data" gets executed as "code" |
| Core | **An LLM's output = untrusted input** | Render AI output as-is and you get the same XSS as a comment field |
| Attack | **Prompt injection** | Direct (chat) / indirect (summarizing a poisoned document) makes the AI emit a payload |
| Defense | How DOMPurify works — and its limits | It sanitizes via the DOM, but **image exfiltration / SSR / URLs** are out of scope |
| Design | Doing it right | Don't build HTML strings / validate (allowlist) / CSP / keep deps updated |

Flow: **[HANDSON.md](./HANDSON.md)**, slides: **[slides/slides.md](./slides/slides.md)**,
speaker script: **[slides/script.md](./slides/script.md)**.

---

## Structure

```
study_XSS/
├─ README.md / HANDSON.md
├─ backend/           FastAPI (uv): AI API (Gemini + auto-fallback + mock) / mock attacker server / comment API
│   ├─ app/ai.py      ← the heart of the AI part
│   └─ .env.example   ← GEMINI_API_KEY (optional)
├─ frontend/          React + TypeScript (bun)
│   └─ src/
│       ├─ render.ts          ← ★ the star: renderLLM(vuln/dompurify/safe)
│       ├─ ai/AiLab.tsx       ← AI lab tab (chat / summarize / render mode / exfil visualization)
│       └─ CommentBoard.tsx   ← basics (plain comment XSS)
└─ slides/            Marp slides (slides.md) + speaker script (script.md)
```

Key idea: **the API only returns JSON (safe)**. XSS happens **where the frontend renders the AI's output**.

---

## Setup

Prerequisites: `uv` (Python) and `bun` (TypeScript). Open two terminals.

### 1) Backend (FastAPI / uv)
```bash
cd backend
# (Optional) only if you want to use Gemini:
#   cp .env.example .env   # then fill in GEMINI_API_KEY
uv run uvicorn app.main:app --reload --port 8000
```
→ API list at http://localhost:8000/docs

### 2) Frontend (React + TS / bun)
```bash
cd frontend
bun install
bun run dev
```
→ Open http://localhost:5173 and go to the **"AI Lab"** tab. Then follow [HANDSON.md](./HANDSON.md).

---

## Gemini API (optional) & Troubleshooting

- **The key is optional.** Without it, the app runs on "mock responses", which is enough to reproduce the attacks (the mock extracts the payload from the input and always fires).
- Create a free key at Google AI Studio (https://aistudio.google.com/apikey) and set `GEMINI_API_KEY=...` in `backend/.env`.
- It tries several models in order; if all fail it **auto-discovers the models actually usable with your key** and retries; if that still fails, it falls back to mock.

**When you're stuck on `provider: mock` (the real AI isn't used):**
1. Hit the diagnostics endpoint → it shows the cause and the usable model names:
   ```bash
   curl http://localhost:8000/api/ai/health
   ```
   If `key_set` is false, the key isn't loaded (place `.env` and restart uvicorn).
   `available_generateContent_models` lists the models usable with this key. `last_error` shows the latest failure reason.
2. **Model names change by time and key.** Old names (e.g. `gemini-2.5-*`) may `404` for new keys; popular models may temporarily `503/429`.
   Defaults: `gemini-3.5-flash → gemini-3-flash-preview → gemini-flash-latest`.
3. To pin them, set `GEMINI_MODELS=name,another-name` in `.env` (pick from the `/api/ai/health` list). Auto-discovery also works.

> Note (important for the lesson): strong models **refuse blatant requests** like "output code that steals cookies."
> The hands-on attack prompts are framed as **innocent-looking requests** ("turn this URL into an image", "show an onerror example").
> That is precisely this material's conclusion: **you must not rely on the model's safety filter.**

---

## API

- `POST /api/ai/chat` … AI chat (for direct injection)
- `POST /api/ai/summarize` … document summarizer (for indirect injection)
- `GET  /api/ai/health` … Gemini connection diagnostics (model list / failure reason)
- `GET  /api/ai/steal` … mock attacker server (receives & records data sent via image/fetch)
- `GET  /api/ai/steal-log` / `DELETE` … list / clear the received "stolen data"
- `GET/POST /api/comments` … the basics comment board

---

## Slides

`slides/slides.md` (Markdown in Marp format, editable). When presenting, read `slides/script.md` alongside.

```bash
bunx @marp-team/marp-cli slides/slides.md --preview   # preview
bunx @marp-team/marp-cli slides/slides.md --pdf        # PDF
bunx @marp-team/marp-cli slides/slides.md --pptx       # PowerPoint
```
In VS Code, the "Marp for VS Code" extension is handy. See [slides/README.md](./slides/README.md) for details.

---

<div align="center">
<sub>All slide decks and hands-on code: <a href="https://github.com/reyquza/study-material-XSS">github.com/reyquza/study-material-XSS</a></sub><br>
<sub>Copyright © 2026 Ray. All rights reserved.</sub>
</div>
