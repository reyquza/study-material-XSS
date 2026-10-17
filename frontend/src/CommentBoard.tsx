import { useEffect, useState } from "react";
import { fetchComments, postComment, resetComments, type Comment } from "./api";
import { renderComment } from "./render";

// 攻撃ペイロードの例。URL内に半角スペース/日本語を入れない（markdownがリンクと解釈できなくなる）。
const PAYLOADS: { label: string; body: string }[] = [
  {
    label: "① markdownリンクの罠（クリックで発火）",
    body: "[🎁 クリックして景品を受け取る](javascript:alert(document.cookie))",
  },
  {
    label: "② img onerror（自動で発火）",
    body: '<img src=x onerror="alert(document.cookie)">',
  },
  {
    label: "③ 文中に紛れた偽リンク",
    body: "詳しくは [公式サイト](javascript:alert('XSS')) をご確認ください",
  },
];

export function CommentBoard() {
  const [comments, setComments] = useState<Comment[]>([]);
  const [author, setAuthor] = useState("名無し");
  const [body, setBody] = useState("");
  const [safeMode, setSafeMode] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    try {
      setComments(await fetchComments());
    } catch (e) {
      setError(String(e));
    }
  }
  useEffect(() => {
    reload();
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    try {
      await postComment(author.trim() || "名無し", body);
      setBody("");
      await reload();
    } catch (e) {
      setError(String(e));
    }
  }

  async function onReset() {
    await resetComments();
    await reload();
  }

  return (
    <div>
      <div className="topbar">
        <p className="hint" style={{ margin: 0 }}>
          基礎パート。コメントは <strong>markdown</strong> 可。攻撃例を投稿し、モードを切り替えて観察。
        </p>
        <label className={`mode ${safeMode ? "safe" : "vuln"}`}>
          <input type="checkbox" checked={safeMode} onChange={(e) => setSafeMode(e.target.checked)} />
          {safeMode ? "対策モード（DOMPurify）" : "脆弱モード（無防備）"}
        </label>
      </div>

      <div className="payloads">
        <span className="payloads__title">攻撃ペイロードを投稿欄に入れる:</span>
        {PAYLOADS.map((p) => (
          <button key={p.label} type="button" onClick={() => setBody(p.body)}>
            {p.label}
          </button>
        ))}
      </div>

      <form className="form" onSubmit={onSubmit}>
        <input
          className="form__author"
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          placeholder="名前"
        />
        <textarea
          className="form__body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="コメントを書く（markdown可）"
          rows={3}
        />
        <div className="form__actions">
          <button type="submit">投稿する</button>
          <button type="button" className="ghost" onClick={onReset}>
            全コメントをリセット
          </button>
        </div>
      </form>

      {error && <p className="error">{error}</p>}

      <ul className="comments">
        {comments.map((c) => (
          <li key={c.id} className="comment">
            <div className="comment__meta">
              <span className="comment__author">{c.author}</span>
              <span className="comment__time">{c.created_at}</span>
            </div>
            {/* 脆弱ポイント: renderComment()の結果を dangerouslySetInnerHTML で描画 */}
            <div
              className="comment__body"
              dangerouslySetInnerHTML={{ __html: renderComment(c.body, safeMode) }}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}
