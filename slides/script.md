# Speaker Script (talk track)

The slides carry only the essentials. This file has the spoken explanations, plain-language
breakdowns of the mechanisms, code walkthroughs, and anticipated Q&A. Keep it open on a second
screen while presenting. ⏱ is a rough time estimate.

> Overall aim: make the audience internalize **"an LLM's output is untrusted input too,"** and
> understand **DOMPurify "by how it works and its limits."**
> Always break down jargon. Deep-dive only three (image exfiltration / SSR / URL); leave the rest as a map.

---

## ① Title (0:00)
- "Today we cover XSS — specifically the kind caused by rendering an LLM's output. The one that hits us as an AI startup hardest."
- "A bit of lecture first, then hands-on: attack → defend → it still leaks → defend properly."

## ② Goals (⏱1 min)
- "Four goals. Above all, take home 'an LLM's output is untrusted input' and 'how DOMPurify works and its limits.'"

## ③ Agenda (⏱30s)
- Announce the timing. "The hands-on + live coding in the second half is the main act."

---

## ④ XSS basics (just this) (⏱3 min) — no demo
- "XSS in one line: input that should be data (just text) ends up being executed as code by the browser."
- Show the one code slide:
  - "Normally in React, `{text}` auto-escapes `<` to `&lt;` and shows it as plain text. Safe."
  - "But `dangerouslySetInnerHTML` changes things. It's the same as doing `element.innerHTML = string` inside."
  - **Mechanism**: "`innerHTML` feeds the string to the browser's HTML parser and **builds real DOM elements**.
     So the string `<img onerror=...>` becomes a real img element + event and starts running. React's auto-escaping is outside this path."
- "If that `text` is untrusted input, it's XSS. And today, that 'untrusted input' is the AI's output."

## ⑤ AI × XSS (hook) (⏱30s)
- "Devs know 'data the user typed is dangerous.' But they tend to render 'AI-generated text' defenselessly, assuming it's safe."
- "Yet the AI's output is exactly the untrusted input an outsider can manipulate."

## ⑥ LLM output = untrusted input (⏱1.5 min)
- "AI chat and summarizers tend to render the AI's markdown directly — they want the formatting (bold, links, images)."
- "Mix attack code in, and it's exactly the same XSS as the comment field. The diagram shows the shape."
- **prompt injection** term: "crafting the instructions to the AI so it produces unintended output."

## ⑦ Two kinds of injection (⏱1.5 min) — stress indirect
- "Direct is when the user themselves asks the AI to 'output this code.'"
- "Indirect is when the instruction is buried in **the external data the AI reads**. The AI passes the poison through while summarizing/quoting."
- "The scary part: the AI doesn't need to do anything bad. **It just carries the poison it was handed,** and the attack succeeds.
   RAG, 'summarize this URL,' 'draft a reply to this inquiry email' — all can be an entry point."

---

## ⑧ Hands-on intro (⏱~27 min from here)
- "Open the 'AI Lab' tab at http://localhost:5173. We'll follow HANDSON.md."
- "The 'render mode' at the top is today's defense level. Toggle Raw / DOMPurify / safe and observe."
- "No key? It falls back to mock automatically. That's plenty to reproduce the attack — don't worry."

## ⑨ First, attack (direct & indirect) (⏱10 min)
- **Direct**: Chat tab → "Direct #1" button → Send. In Raw render, the image loads and the secret lands in the attacker panel.
  - "You just asked the AI to turn a URL into an image, and the moment it rendered, data leaked."
- **Indirect**: Summarizer tab → "Indirect #1" button → Summarize. The poisoned doc's banner image survives into the summary; **the moment the image loads, data exfiltrates**.
  - "The AI 'just summarized.' But it obeyed the instruction buried in the document and emitted an image that sends the secret out."
- Confirm everyone sees "stolen data" appear in the panel (call it out on the video call).

## ⑩ Defense #1: DOMPurify, from how it works (⏱4 min)
- "Let's fix it. Switch render mode to DOMPurify. First, correctly understand what it does."
- **Mechanism (not a black box)**:
  - "DOMPurify isn't deleting things with regex. It **builds the incoming HTML string into a real DOM (tree)**,
     **removes dangerous nodes/attributes/URLs (onerror attribute, javascript: href) from the tree**, and returns safe HTML."
- **Order note**: "Always 'Markdown → HTML' first, THEN 'sanitize.' Reversed, symbols (< >) break or the converted HTML slips through."
- "This removes Direct #2's `onerror` and stops cookie theft. …But that's not the end. Here's the real part."

## ⑪ Bypass 1: image exfiltration (⏱3 min) — the shocker
- "Stay in DOMPurify mode and run Indirect #1 (the image one) again. …**It still leaks.**"
- **Why?**: "DOMPurify allows `<img>` as a 'legitimate tag.' So the `![](…/steal?c=secret)` image survives.
   The browser fetches it. The secret in the URL reaches the attacker. **Not a single line of JS.**"
- "Removing onerror doesn't help. This is a case where 'cleaning the output' isn't enough."
- **Defense**: "Restrict image src to your own origin + block external images with CSP `img-src`.
   You need the mindset of constraining 'where it's allowed to connect.'"
  - CSP note: "CSP declares to the browser where the page may connect/execute. `img-src 'self'` blocks all external images."
- "Switch to safe mode and the external image is removed — you can confirm the leak stops."

## ⑫ Bypass 2: DOMPurify doesn't work under SSR (⏱3 min) — connect via principle
- "Remember I said 'DOMPurify works using the DOM'? It pays off here."
- "Using the DOM means **it can't work where there's no DOM**. Next.js SSR — generating HTML on the server — has no browser DOM."
- **Risk**: "Calling DOMPurify as-is on the server either errors or doesn't sanitize correctly.
   You need to wire in `jsdom` (a fake browser), but a misconfig lets it **slip through on the server**, riding raw HTML into the page.
   It fires the moment it reaches the client. 'Sanitize later on the client' is too late."
- **Guidance**: "Render AI output safely by **sanitizing on the client (after mount)**, not on the server.
   Best of all, don't build HTML strings — build elements with react-markdown."

## ⑬ Bypass 3: link URLs are outside DOMPurify (⏱2.5 min)
- "What DOMPurify cleans is an 'HTML string.' But if you take the AI's returned URL and pass it to `<a href={url}>` or Next.js `<Link href={url}>` yourself,
   that's not HTML — it's a 'prop.' **It never went through DOMPurify.**"
- "So if `url = 'javascript:alert(document.cookie)'`, it fires on click. No amount of HTML cleaning matters."
- **Defense**: "Validate the URL scheme yourself. `new URL()` and allow only `http`/`https`.
   'We sanitized, so we're safe' falls apart if the JS logic is bad."

## ⑭ More pitfalls (⏱2 min) — just a map
- "Three deep dives are enough. Keep the rest in the back of your mind."
- Wrong order (convert vs sanitize) / config self-destruct (allowing iframe etc.) / mXSS.
- mXSS note: "An advanced bug where the browser's own re-parsing/optimization turns HTML that DOMPurify deemed 'safe' into dangerous code.
   So it's not 'add it and you're done' — keeping the library up to date (Dependabot etc.) is the defense."

## ⑮ Designing it right (conclusion) (⏱1.5 min)
- Read the five points. "The root is one thing: **treat the AI's output as untrusted input, too.** If nothing else, take this home."

## ⑯ The full picture (⏱1 min)
- "Separate primary defenses (output sanitization + URL/image validation) from safety nets (CSP, HttpOnly, updates).
   'CSP so we're safe' / 'HttpOnly so we're safe' are misconceptions. Safety nets don't replace the root fix."

## ⑰ Wrap-up (⏱1 min)
- Read the checklist.

## ⑱ Learn more
- "For LLM-specific risks, OWASP Top 10 for LLM; for XSS in general, PortSwigger's labs. I learned hands-on there myself."
- Go to Q&A.

---

## Anticipated Q&A (for the tough reviewer)
- **Q: Why not trust the AI's output? Isn't the model ours?**
  A: The output depends on the input (prompt / external document). With indirect injection, a third party effectively controls the output. So it's "untrusted input."
- **Q: Isn't adding DOMPurify enough?**
  A: By design, image-based exfiltration and URLs (via props) are out of scope. There's also the trap of it not working under SSR. You need validation + CSP + design.
- **Q: Is react-markdown safe?**
  A: By default it builds elements and blocks `javascript:`, so it's on the safe side. But enabling raw HTML with `rehype-raw` opens a hole (you must pair it with `rehype-sanitize`).
- **Q: Won't Gemini block dangerous output?**
  A: An XSS payload isn't "harmful content," it's just code, so it usually passes through. Also, today's indirect type keeps the payload in the document, so it doesn't depend on the model's judgment.
- **Q: Is the server (FastAPI) in this demo vulnerable?**
  A: The server just returns JSON; no XSS there. The vulnerable part is the frontend render. It's designed that way on purpose.
- **Q: Are the alert and steal real harm?**
  A: The alert proves "code executed." steal is a local mock attacker server; nothing is sent outside (it's teaching material).
