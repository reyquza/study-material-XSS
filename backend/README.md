# backend — FastAPI（AI output XSS + Comment API）

AIを呼んでテキストを返すAPIと、基礎パートのコメントAPI。どちらも**JSONを返すだけ**で、
XSSはフロントの描画で起きます（APIは安全）。

## Run
```bash
cd backend
# （任意）Geminiを使うなら: cp .env.example .env して GEMINI_API_KEY を記入
uv run uvicorn app.main:app --reload --port 8000
```
`uv run` がPython・仮想環境・依存の用意まで自動。API一覧: http://localhost:8000/docs

## AI endpoints（`app/ai.py`）
- `POST /api/ai/chat` … AIチャット（直接インジェクション用）
- `POST /api/ai/summarize` … 文書要約（間接インジェクション用）
- `GET  /api/ai/health` … **Gemini接続の診断**（使えるモデル一覧・直近の失敗理由）
- `GET  /api/ai/steal?c=...` … **模擬攻撃者サーバ**。画像/fetchで送られた"盗難データ"を記録し1x1 GIFを返す
- `GET  /api/ai/steal-log` / `DELETE /api/ai/steal-log` … 盗難データの一覧 / クリア

## Gemini & フォールバック
- `GEMINI_API_KEY` が**あれば** Gemini を呼ぶ。複数モデルを順に試し、失敗したら次へ。
  全滅したら **ListModels で「このキーで使えるモデル」を自動検出**して再試行。それでもダメならモック。
- `GEMINI_API_KEY` が**無ければ**最初からモック。→ キー無しでもハンズオンが成立（当日落ちない）。
- モックは入力(プロンプト/文書)から payload（画像・imgタグ・URL）を取り出して出力に通す。
  → 「間接インジェクション＝AIは毒を素通しするだけ」の忠実な再現。

### `provider: mock` から抜けられないとき
```bash
curl http://localhost:8000/api/ai/health
```
- `key_set: false` → `.env` が読まれていない（置いて uvicorn 再起動）。
- `available_generateContent_models` → このキーで使える名前。既定が含まれなければ 404 で全滅する。
  → `.env` に `GEMINI_MODELS=<available の名前>` を設定（自動検出でも復帰します）。
- `last_error` → 直近の失敗理由（404=モデル無し / 503,429=混雑・レート制限 など）。

> 教材メモ: 強いモデルは露骨な「Cookie窃取コードを出して」は拒否する。ハンズオンは
> 「URLを画像にして」「onerrorの例を見せて」等の**無害に見える依頼**で payload を出させている。
> ＝「モデルの安全フィルタに頼れない」という結論の実演。

## Comment API（基礎パート）
- `GET /api/comments` / `POST /api/comments` / `DELETE /api/comments`
- 本文(markdown)を**無害化せず**保存・返却。XSSはフロントの描画で起きる。

> 教材のためわざと脆弱。本番にコピーしないこと。`/api/ai/steal` は外部に一切送信しません（ローカル記録のみ）。
