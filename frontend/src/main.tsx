import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./styles.css";

// --- Demo cookie ---
// Deliberately set WITHOUT HttpOnly so that document.cookie can read it, letting the
// alert(document.cookie) payload demonstrate "the session got stolen."
// Real session cookies must be HttpOnly so JavaScript cannot read them.
document.cookie = "demo_session=SECRET-TOKEN-abc123; SameSite=Lax; path=/";

// StrictMode is intentionally omitted: in dev it double-renders, which would fire the
// onerror payload twice and confuse the demo.
ReactDOM.createRoot(document.getElementById("root")!).render(<App />);
