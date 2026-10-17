export type Comment = {
  id: number;
  author: string;
  body: string;
  created_at: string;
};

// vite proxy 経由でバックエンド(8000)に届く。
const BASE = "/api/comments";

export async function fetchComments(): Promise<Comment[]> {
  const res = await fetch(BASE);
  if (!res.ok) throw new Error(`一覧取得に失敗: ${res.status}`);
  return res.json();
}

export async function postComment(author: string, body: string): Promise<Comment> {
  const res = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ author, body }),
  });
  if (!res.ok) throw new Error(`投稿に失敗: ${res.status}`);
  return res.json();
}

export async function resetComments(): Promise<void> {
  await fetch(BASE, { method: "DELETE" });
}
