import { useState } from "react";
import { AiLab } from "./ai/AiLab";
import { CommentBoard } from "./CommentBoard";

export function App() {
  const [view, setView] = useState<"ai" | "comment">("ai");

  return (
    <div className="page">
      <header className="apphead">
        <h1>XSS Security Lab</h1>
        <nav className="nav">
          <button className={view === "ai" ? "on" : ""} onClick={() => setView("ai")}>
            AI Lab (main)
          </button>
          <button className={view === "comment" ? "on" : ""} onClick={() => setView("comment")}>
            Comment Board (basics)
          </button>
        </nav>
      </header>

      {view === "ai" ? <AiLab /> : <CommentBoard />}

      <footer className="foot">
        Intentionally vulnerable for learning. Only attack your own local environment. Never copy this code into production.
      </footer>
    </div>
  );
}
