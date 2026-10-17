import { useState } from "react";
import { AiLab } from "./ai/AiLab";
import { CommentBoard } from "./CommentBoard";

export function App() {
  const [view, setView] = useState<"ai" | "comment">("ai");

  return (
    <div className="page">
      <header className="apphead">
        <h1>XSS 勉強会</h1>
        <nav className="nav">
          <button className={view === "ai" ? "on" : ""} onClick={() => setView("ai")}>
            AI実習（メイン）
          </button>
          <button className={view === "comment" ? "on" : ""} onClick={() => setView("comment")}>
            コメント掲示板（基礎）
          </button>
        </nav>
      </header>

      {view === "ai" ? <AiLab /> : <CommentBoard />}

      <footer className="foot">
        教材のため、わざと脆弱に作っています。攻撃の練習は自分のローカル環境だけで。本番コードにコピーしないこと。
      </footer>
    </div>
  );
}
