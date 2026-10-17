import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./styles.css";

// --- デモ用のダミーCookie ---
// document.cookie で読めるようにわざと HttpOnly なしで置いている。
// 攻撃ペイロード alert(document.cookie) で「セッションが盗まれる」様子を体感するため。
// 本番のセッションCookieは HttpOnly を付け、JSから読めないようにするのが鉄則。
document.cookie = "demo_session=SECRET-TOKEN-abc123; SameSite=Lax; path=/";

// 注意: StrictMode は付けていない。
// 開発時の二重描画で onerror ペイロードが2回発火し、デモ中に混乱するのを避けるため。
ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
