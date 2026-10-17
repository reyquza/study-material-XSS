"""
勉強会用: コメント掲示板のバックエンド (FastAPI)

【設計の意図 — ここが今日の肝】
- このAPIは「コメント本文(markdownの生テキスト)」をそのまま保存し、JSONで返すだけ。
- レスポンスは Content-Type: application/json なので、ブラウザはこれを「HTML」として
  レンダリングしない。つまり *APIレイヤ単体ではXSSは起きにくい*。
- XSSが起きるのは、フロント(React)がこのJSONを受け取って画面に *描画* する所。
  → 「モダンなAPI+SPA構成では、XSSはサーバではなくフロントの描画レイヤに引っ越す」

※このコードは教材。本番にそのまま使わないこと。
"""

from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.ai import router as ai_router

# backend/.env から GEMINI_API_KEY を読む(任意。無ければモックで動く)。
load_dotenv()

app = FastAPI(title="XSS 勉強会教材 (コメント掲示板 + AI出力XSS)")

# フロント(Vite dev server)からのアクセスを許可。
# ※フロント側の vite proxy を使えば同一オリジンになるのでCORSは不要だが、
#   直接叩く人のために保険で入れておく。
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    """多層防御の一例: MIMEスニッフィングを禁止。
    これで「JSONのつもりがHTMLとして実行される」事故を防ぐ。"""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


class CommentIn(BaseModel):
    author: str = Field(default="名無し", max_length=40)
    body: str = Field(..., max_length=2000)  # markdownの生テキスト


class Comment(CommentIn):
    id: int
    created_at: str


# インメモリ保存(サーバ再起動でリセット)。DBを使わないのはデモを単純にするため。
_comments: list[Comment] = []
_next_id = 1


def _add(author: str, body: str) -> Comment:
    global _next_id
    c = Comment(
        id=_next_id,
        author=author,
        body=body,
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    _comments.append(c)
    _next_id += 1
    return c


def _seed() -> None:
    _add("運営", "ようこそ！ここにコメントを投稿してみてください。**markdown** も使えます 🎉")
    _add("たろう", "勉強会たのしみ！[参考リンク](https://owasp.org) を貼っておきます。")


_seed()


@app.get("/api/comments", response_model=list[Comment])
def list_comments() -> list[Comment]:
    return _comments


@app.post("/api/comments", response_model=Comment)
def create_comment(payload: CommentIn) -> Comment:
    # ★意図的に無害化しない: 生のmarkdownをそのまま保存する。
    #   「入力を保存する段階では文脈が決まらない」ことの表現でもある。
    return _add(payload.author or "名無し", payload.body)


@app.delete("/api/comments")
def reset_comments() -> dict:
    """デモをやり直すためのリセット。"""
    global _comments, _next_id
    _comments = []
    _next_id = 1
    _seed()
    return {"status": "reset"}


app.include_router(ai_router)


@app.get("/")
def health() -> dict:
    return {"service": "xss-study", "docs": "/docs"}
