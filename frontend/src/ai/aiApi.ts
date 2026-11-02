// Backend AI endpoints (reached via the vite proxy to :8000).

export type AiOut = {
  text: string; // the LLM's output (raw markdown)
  provider: string; // the model that answered, or "mock"
  note: string;
};

export async function aiChat(message: string): Promise<AiOut> {
  const res = await fetch("/api/ai/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error(`chat failed: ${res.status}`);
  return res.json();
}

export async function aiSummarize(document: string): Promise<AiOut> {
  const res = await fetch("/api/ai/summarize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document }),
  });
  if (!res.ok) throw new Error(`summarize failed: ${res.status}`);
  return res.json();
}

export type StealLog = { count: number; entries: { stolen: string }[] };

export async function fetchStealLog(): Promise<StealLog> {
  const res = await fetch("/api/ai/steal-log");
  if (!res.ok) throw new Error(`steal-log failed: ${res.status}`);
  return res.json();
}

export async function clearStealLog(): Promise<void> {
  await fetch("/api/ai/steal-log", { method: "DELETE" });
}
