"""
Backend for the comment board (FastAPI).

[Design intent — the key point]
- This API just stores the "comment body (raw markdown text)" as-is and returns it as JSON.
- The response is Content-Type: application/json, so the browser does NOT render it as "HTML".
  In other words, *XSS is unlikely at the API layer alone*.
- XSS happens where the frontend (React) takes this JSON and *renders* it on screen.
  → "In a modern API + SPA architecture, XSS moves from the server to the frontend render layer."

NOTE: this code is teaching material. Do not use it as-is in production.
"""

from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.ai import router as ai_router

# Read GEMINI_API_KEY from backend/.env (optional; without it the app runs on mock).
load_dotenv()

app = FastAPI(title="XSS Security Lab (comment board + LLM-output XSS)")

# Allow access from the frontend (Vite dev server).
# Using the frontend's vite proxy makes it same-origin so CORS isn't required,
# but we keep this as a safety net for people hitting the API directly.
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
    """One example of defense-in-depth: forbid MIME sniffing.
    This prevents the "JSON gets executed as HTML" accident."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


class CommentIn(BaseModel):
    author: str = Field(default="Anonymous", max_length=40)
    body: str = Field(..., max_length=2000)  # raw markdown text


class Comment(CommentIn):
    id: int
    created_at: str


# In-memory storage (reset on server restart). No DB, to keep the demo simple.
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
    _add("Admin", "Welcome! Try posting a comment below. **Markdown** works too 🎉")
    _add("alice", "Excited for this! Here's a [reference link](https://owasp.org).")


_seed()


@app.get("/api/comments", response_model=list[Comment])
def list_comments() -> list[Comment]:
    return _comments


@app.post("/api/comments", response_model=Comment)
def create_comment(payload: CommentIn) -> Comment:
    # Intentionally NOT sanitized: store the raw markdown as-is.
    # This also expresses that "at store time, the output context isn't yet decided."
    return _add(payload.author or "Anonymous", payload.body)


@app.delete("/api/comments")
def reset_comments() -> dict:
    """Reset, to restart the demo."""
    global _comments, _next_id
    _comments = []
    _next_id = 1
    _seed()
    return {"status": "reset"}


app.include_router(ai_router)


@app.get("/")
def health() -> dict:
    return {"service": "xss-study", "docs": "/docs"}
