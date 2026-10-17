// バックエンドのAIエンドポイント(vite proxy 経由で :8000 に届く)。

export type AiOut = {
  text: string; // LLMの出力(生markdown)
  provider: string; // 応答したモデル名 or "mock"
  note: string;
};

export async function aiChat(message: string): Promise<AiOut> {
  const res = await fetch("/api/ai/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error(`chat失敗: ${res.status}`);
  return res.json();
}

export async function aiSummarize(document: string): Promise<AiOut> {
  const res = await fetch("/api/ai/summarize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document }),
  });
  if (!res.ok) throw new Error(`summarize失敗: ${res.status}`);
  return res.json();
}

export type StealLog = { count: number; entries: { stolen: string }[] };

export async function fetchStealLog(): Promise<StealLog> {
  const res = await fetch("/api/ai/steal-log");
  if (!res.ok) throw new Error(`steal-log失敗: ${res.status}`);
  return res.json();
}

export async function clearStealLog(): Promise<void> {
  await fetch("/api/ai/steal-log", { method: "DELETE" });
}
