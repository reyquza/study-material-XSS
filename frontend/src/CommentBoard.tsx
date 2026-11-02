import { useEffect, useState } from "react";
import { fetchComments, postComment, resetComments, type Comment } from "./api";
import { renderComment } from "./render";

// Attack payloads. Keep NO ASCII spaces / non-ASCII inside the URL part of a Markdown link,
// otherwise Markdown won't parse it as a link (it becomes plain text).
const PAYLOADS: { label: string; body: string }[] = [
  {
    label: "#1 Markdown link trap (fires on click)",
    body: "[🎁 Click to claim your prize](javascript:alert(document.cookie))",
  },
  {
    label: "#2 img onerror (fires automatically)",
    body: '<img src=x onerror="alert(document.cookie)">',
  },
  {
    label: "#3 fake link hidden in a sentence",
    body: "See the [official site](javascript:alert('XSS')) for details",
  },
];

export function CommentBoard() {
  const [comments, setComments] = useState<Comment[]>([]);
  const [author, setAuthor] = useState("Anonymous");
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
      await postComment(author.trim() || "Anonymous", body);
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
          Basics. Comments support <strong>markdown</strong>. Post an attack example and toggle the mode to observe.
        </p>
        <label className={`mode ${safeMode ? "safe" : "vuln"}`}>
          <input type="checkbox" checked={safeMode} onChange={(e) => setSafeMode(e.target.checked)} />
          {safeMode ? "Safe mode (DOMPurify)" : "Vulnerable mode (defenseless)"}
        </label>
      </div>

      <div className="payloads">
        <span className="payloads__title">Load an attack payload into the box:</span>
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
          placeholder="Name"
        />
        <textarea
          className="form__body"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Write a comment (markdown allowed)"
          rows={3}
        />
        <div className="form__actions">
          <button type="submit">Post</button>
          <button type="button" className="ghost" onClick={onReset}>
            Reset all comments
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
            {/* Vulnerable spot: renderComment()'s output goes into dangerouslySetInnerHTML */}
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
