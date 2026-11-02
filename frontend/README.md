# frontend — React + TypeScript

Fetches the LLM output / comments from the backend and renders them on screen. **XSS happens here.**

## Run
```bash
cd frontend
bun install
bun run dev
```
→ http://localhost:5173

Start the backend first (`/api` reaches :8000 via the vite proxy).

## Files

| File | Role |
|---|---|
| `src/render.ts` | **The star.** markdown→HTML + sanitization. `renderLLM(vuln/dompurify/safe)` and `renderComment`. |
| `src/ai/AiLab.tsx` | AI Lab tab: chat / summarizer, render-mode toggle, attacker-receive panel. |
| `src/ai/aiApi.ts` | Calls the backend AI endpoints. |
| `src/CommentBoard.tsx` | Basics: plain comment XSS. |
| `src/App.tsx` | Shell with tab navigation. |
| `src/main.tsx` | Bootstrap + a demo cookie (no HttpOnly, on purpose). |

## Key points (`src/render.ts`)

- Rendering uses `dangerouslySetInnerHTML`.
- `marked` (the markdown library) **does not sanitize** (by design) → fires in the "vuln" mode.
- `DOMPurify` (sanitizer) neutralizes JS-based payloads → but **image exfiltration still gets through** in plain "dompurify" mode.
- The "safe" mode adds a URL-scheme allowlist and drops external-origin images.
- React's built-in protection on `{text}` / `href={url}` **does not apply** once you use `dangerouslySetInnerHTML`.
  That's the "it's React, so it's safe" pitfall.

## If you hit type errors

If `dompurify` types are missing, run `bun add -d @types/dompurify` (usually unnecessary — most versions ship their own types).
