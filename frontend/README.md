# frontend — React + TypeScript のコメント画面

バックエンドからコメント(markdown)を取得し、画面に描画します。**XSSはここで起きます。**

## 起動

```bash
cd frontend
bun install
bun run dev
```

→ http://localhost:5173

※先に backend を起動しておくこと（`/api` は vite proxy 経由で 8000 に届きます）。

## ファイル

| ファイル | 役割 |
|---|---|
| `src/App.tsx` | 画面本体。投稿フォーム、脆弱/対策トグル、コメント描画 |
| `src/render.ts` | **今日の主役**。markdown→HTML変換とサニタイズ。`safeMode` で挙動が変わる |
| `src/api.ts` | バックエンドAPI呼び出し |
| `src/main.tsx` | 起動 + デモ用のダミーCookie設定 |

## 重要ポイント（`src/App.tsx` / `src/render.ts`）

- 描画は `dangerouslySetInnerHTML` で行っている。
- `marked`（markdownライブラリ）は **無害化しない**（公式仕様）。→ 脆弱モードで発火。
- `DOMPurify`（サニタイザ）で無害化 → 対策モードで防御成功。
- React標準の `{c.body}` や `href={url}` の保護は、`dangerouslySetInnerHTML` を使うと **効かない**。
  これが「Reactだから安全」の落とし穴。

## 型エラーが出たら

`dompurify` の型が見つからない等が出た場合は `bun add -d @types/dompurify` を実行してください
（多くのバージョンでは型が同梱されているため不要です）。
