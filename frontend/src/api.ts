export type Comment = {
  id: number;
  author: string;
  body: string;
  created_at: string;
};

// Reaches the backend (:8000) via the vite proxy.
const BASE = "/api/comments";

export async function fetchComments(): Promise<Comment[]> {
  const res = await fetch(BASE);
  if (!res.ok) throw new Error(`Failed to fetch comments: ${res.status}`);
  return res.json();
}

export async function postComment(author: string, body: string): Promise<Comment> {
  const res = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ author, body }),
  });
  if (!res.ok) throw new Error(`Failed to post comment: ${res.status}`);
  return res.json();
}

export async function resetComments(): Promise<void> {
  await fetch(BASE, { method: "DELETE" });
}
