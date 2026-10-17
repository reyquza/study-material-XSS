import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// フロントの /api/* をバックエンド(8000)へ中継する。
// これで同一オリジン扱いになり、CORSを気にせず fetch("/api/comments") できる。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
