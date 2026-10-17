# Introduction to XSS
## ~ Modern XSS Hands-on Training Material ~

**わざと脆弱に作ったAIアプリ**を各自のPCで動かし、
「AIの出力を画面に描画する」ことで起きる **XSS / 情報漏洩** を、攻撃 → 対策の順で体験します。

> ⚠️ **重要**: このコードは *学習目的でわざと脆弱に* 作られています。**本番コードにコピーしないでください。**
> 攻撃の練習は **自分のローカル環境だけ** で。盗んだ風のデータも外部へは一切送りません
> （`/api/ai/steal` はローカルの模擬攻撃者サーバ）。

---

## Learning Objectives

| 段階 | テーマ | ひとことで |
|---|---|---|
| 基礎 | XSSとは | 「データ」のはずの入力が「コード」として実行される |
| 核心 | **AIの出力 = 信頼できない入力** | AI出力をそのまま描画すればコメント欄と同じXSSになる |
| 攻撃 | **prompt injection** | 直接（チャット）/ 間接（毒入り文書の要約）でAIに payload を出力させる |
| 対策 | DOMPurify の仕組みと限界 | DOMを使って無害化する。でも**画像漏洩・SSR・URL**は守備範囲外 |
| 設計 | 正しい防御 | HTML文字列を作らない / 検証（許可リスト）/ CSP / 依存最新化 |

進行は **[HANDSON.md](./HANDSON.md)**、スライドは **[slides/slides.md](./slides/slides.md)**、
発表カンペは **[slides/原稿.md](./slides/原稿.md)**。

---

## Structure

```
study_XSS/
├─ README.md / HANDSON.md
├─ backend/           FastAPI（uv）: AIを呼ぶAPI(Gemini+自動フォールバック+モック) / 模擬攻撃者サーバ / コメントAPI
│   ├─ app/ai.py      ← AIパートの本体
│   └─ .env.example   ← GEMINI_API_KEY（任意）
├─ frontend/          React + TypeScript（bun）
│   └─ src/
│       ├─ render.ts          ← ★主役: renderLLM(vuln/dompurify/safe)
│       ├─ ai/AiLab.tsx       ← AI実習タブ（チャット/要約/描画モード/漏洩可視化）
│       └─ CommentBoard.tsx   ← 基礎パート（素のコメントXSS）
└─ slides/            Marpスライド（slides.md）+ 発表原稿（原稿.md）
```

ポイント: **APIはJSONを返すだけ（安全）**。XSSは **フロントがAIの出力を描画する所** で起きます。

---

## Setup

前提: `uv`（Python）と `bun`（TypeScript）。ターミナルを2つ開きます。

### 1) Backend（FastAPI / uv）
```bash
cd backend
# （任意）Geminiを使う場合のみ:
#   cp .env.example .env   # そして GEMINI_API_KEY を記入
uv run uvicorn app.main:app --reload --port 8000
```
→ http://localhost:8000/docs でAPI一覧。

### 2) Frontend（React + TS / bun）
```bash
cd frontend
bun install
bun run dev
```
→ http://localhost:5173 を開き、**「🤖 AI実習」** タブへ。あとは [HANDSON.md](./HANDSON.md) に沿って。

---

## Gemini API（任意）と Troubleshooting

- **キーは任意。** 未設定でも「モック応答」で動き、攻撃の再現には充分（モックは入力から payload を取り出して必ず発火）。
- キーは Google AI Studio（https://aistudio.google.com/apikey ）で無料発行し、`backend/.env` に `GEMINI_API_KEY=...`。
- 複数モデルを順に試し、全滅したら**このキーで実際に使えるモデルを自動検出**して再試行、それでもダメならモックへ。

**「`provider: mock` になって本物のAIが使われない」とき:**
1. 診断エンドポイントを叩く → 原因と「使えるモデル名」が見える:
   ```bash
   curl http://localhost:8000/api/ai/health
   ```
   `key_set` が false ならキー未反映（`.env` を置いて uvicorn を再起動）。
   `available_generateContent_models` が、このキーで使えるモデル一覧。`last_error` に直近の失敗理由。
2. **モデル名は時期・キーで変わります。** 古い名前（例 `gemini-2.5-*`）は新規キーで `404`、人気モデルは一時的に `503/429` になることがあります。
   既定は `gemini-3.5-flash → gemini-3-flash-preview → gemini-flash-latest`。
3. 明示したいときは `.env` に `GEMINI_MODELS=モデル名,別のモデル名`（`/api/ai/health` の一覧から選ぶ）。自動検出に任せてもOK。

> 補足（教材的に重要）: 強いモデルは「Cookieを盗むコードを出して」のような**露骨な依頼は拒否**します。
> ハンズオンの攻撃プロンプトは「URLを画像にして」「onerrorの例を見せて」など**無害に見える依頼**に仕立てています。
> これは「**モデルの安全フィルタに頼ってはいけない**」という本教材の結論そのものです。

---

## API

- `POST /api/ai/chat` … AIチャット（直接インジェクション用）
- `POST /api/ai/summarize` … 文書要約（間接インジェクション用）
- `GET  /api/ai/health` … Gemini接続の診断（モデル一覧・失敗理由）
- `GET  /api/ai/steal` … 模擬攻撃者サーバ（画像/fetchで盗んだデータを受信・記録）
- `GET  /api/ai/steal-log` / `DELETE` … 受信した"盗難データ"の一覧 / クリア
- `GET/POST /api/comments` … 基礎パートのコメント掲示板

---

## Slides

`slides/slides.md`（Marp形式のMarkdown、編集可）。発表時は `slides/原稿.md` を見ながら話す前提です。

```bash
bunx @marp-team/marp-cli slides/slides.md --preview   # プレビュー
bunx @marp-team/marp-cli slides/slides.md --pdf        # PDF
bunx @marp-team/marp-cli slides/slides.md --pptx       # PowerPoint
```
VS Code なら拡張機能「Marp for VS Code」が便利。詳細は [slides/README.md](./slides/README.md)。

---

<div align="center">
<sub>All slide decks and hands-on codes: <a href="https://github.com/reyquza/study-material-XSS">github.com/reyquza/study-material-XSS</a></sub><br>
<sub>Copyright © 2026 Ray. All rights reserved.</sub>
</div>
