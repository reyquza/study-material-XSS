"""
AIパート: 「LLMの出力をそのまま画面に出す」XSSを体験するためのバックエンド。

設計の芯:
- LLMの出力は "信頼できない入力" の一種。コメントと全く同じ扱いが必要。
- ここ(バックエンド)は Gemini を呼んでテキストを返すだけ。XSSは例によってフロントの描画で起きる。

Gemini まわりの作り(ご要望対応):
- 複数モデルを順に試す「フォールバック」。失敗したら次のモデルへ。
- 設定したモデル名が全滅したら、ListModels APIで「このキーで実際に使えるモデル」を自動検出して再試行。
  → モデル名を当てずっぽうで書かなくても動く。
- 失敗理由(HTTPステータス・本文)は _last_error に記録し、/api/ai/health と応答のnoteで見える化。
- それでもダメ / キー未設定 なら「モック応答」にフォールバック(当日落ちない保険)。
"""

from __future__ import annotations

import os
import re
from typing import Literal

import httpx
from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/ai", tags=["ai"])

BASE = "https://generativelanguage.googleapis.com/v1beta"

# 既定で試すモデル。環境変数 GEMINI_MODELS="a,b,c" で上書き可。
# ※ここが全滅しても、後述の「自動検出」で実在モデルに切り替わるので神経質にならなくてよい。
# ※モデルの提供状況はキー/時期で変わる。古いモデル(例 gemini-2.5-*)は新規キーで404になることがある。
#   実際に使える名前は GET /api/ai/health で確認できる。
DEFAULT_MODELS = ["gemini-3.5-flash", "gemini-3-flash-preview", "gemini-flash-latest"]

_last_error: str = ""  # 直近の失敗理由(health / note 表示用)


def _api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def _models() -> list[str]:
    raw = os.environ.get("GEMINI_MODELS", "").strip()
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    return DEFAULT_MODELS


class ChatIn(BaseModel):
    message: str = Field(..., max_length=4000)


class SummarizeIn(BaseModel):
    document: str = Field(..., max_length=8000)


class AiOut(BaseModel):
    text: str           # LLMの出力(生のmarkdown/テキスト)
    provider: str       # 実際に応答したモデル名 or "mock"
    note: str = ""      # フォールバックの説明など(UI表示用)


async def _list_available(client: httpx.AsyncClient, api_key: str) -> list[str]:
    """このキーで generateContent が使えるモデル名を取得する。"""
    try:
        r = await client.get(f"{BASE}/models", headers={"x-goog-api-key": api_key})
    except httpx.HTTPError:
        return []
    if r.status_code != 200:
        return []
    names: list[str] = []
    for m in r.json().get("models", []):
        if "generateContent" in m.get("supportedGenerationMethods", []):
            names.append(m.get("name", "").removeprefix("models/"))
    return [n for n in names if n]


async def _generate(
    client: httpx.AsyncClient, api_key: str, model: str, system: str, user: str
) -> tuple[str, str] | None:
    """1モデルで生成。成功で (text, model)。失敗は _last_error に理由を残して None。"""
    global _last_error
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.4},
    }
    try:
        r = await client.post(
            f"{BASE}/models/{model}:generateContent",
            headers={"x-goog-api-key": api_key},
            json=body,
        )
    except httpx.HTTPError as e:
        _last_error = f"{model}: ネットワークエラー ({e!r})"
        return None
    if r.status_code != 200:
        _last_error = f"{model}: HTTP {r.status_code} {r.text[:300]}"
        return None
    data = r.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        # 候補なし = 安全フィルタでブロック等。理由を残す。
        _last_error = f"{model}: 候補なし {str(data)[:300]}"
        return None
    if not text:
        _last_error = f"{model}: 空応答"
        return None
    return text, model


async def _call_gemini(system: str, user: str) -> tuple[str, str] | None:
    global _last_error
    api_key = _api_key()
    if not api_key:
        return None
    _last_error = ""
    async with httpx.AsyncClient(timeout=25) as client:
        tried: list[str] = []
        # 1) 設定モデルを順に
        for model in _models():
            tried.append(model)
            res = await _generate(client, api_key, model, system, user)
            if res:
                return res
        # 2) 全滅 → 実在モデルを自動検出して再試行(flash優先)
        available = await _list_available(client, api_key)
        retry = [m for m in available if "flash" in m and m not in tried]
        retry += [m for m in available if m not in tried and m not in retry]
        for model in retry[:3]:
            res = await _generate(client, api_key, model, system, user)
            if res:
                return res
        if available:
            _last_error += f" ｜ このキーで使えるモデル: {', '.join(available[:10])}"
        else:
            _last_error += " ｜ ListModelsも取得不可(キー/権限/ネットワークを確認)"
    return None


_IMG_MD = re.compile(r"!\[[^\]]*\]\([^)]+\)")
_IMG_TAG = re.compile(r"<img[^>]*>", re.I)
_URL = re.compile(r"https?://[^\s)\]\"'<>]+")


def _mock(user: str, kind: Literal["chat", "summarize"]) -> str:
    """キー無し/全滅時のモック。「compliantなLLM」を演じ、入力から payload を取り出して出力する。
    - 入力に既にある画像/imgタグ → そのまま通す(間接injectionの忠実再現)
    - URLだけある → 画像記法に包む
    - onerror を要求している → onerror付きimgを出す
    これで、実Geminiが使えない人でも攻撃が確実に再現できる。
    """
    payloads = _IMG_MD.findall(user) + _IMG_TAG.findall(user)
    if not payloads:
        m = _URL.search(user)
        if m:
            payloads = [f"![leak]({m.group(0)})"]
        elif "onerror" in user.lower():
            payloads = ["<img src=x onerror=\"alert('XSS')\">"]
    body = "\n\n".join(payloads) if payloads else "（危険な内容は見つかりませんでした）"
    if kind == "summarize":
        return "（モック要約）要点:\n\n- サンプル文書です。\n\n" + body
    return "（モック応答）はい、こちらです:\n\n" + body


async def _run(system: str, user: str, kind: Literal["chat", "summarize"]) -> AiOut:
    result = await _call_gemini(system, user)
    if result is not None:
        text, model = result
        return AiOut(text=text, provider=model)
    if not _api_key():
        note = "GEMINI_API_KEY 未設定のためモック応答"
    else:
        note = f"Gemini応答不可→モック: {_last_error}"
    return AiOut(text=_mock(user, kind), provider="mock", note=note)


@router.post("/chat", response_model=AiOut)
async def chat(payload: ChatIn) -> AiOut:
    """(a) 直接インジェクション用。ユーザーの指示でAIに payload を出力させる。"""
    system = (
        "あなたは親切なアシスタントです。回答は markdown で、"
        "必要なら太字・箇条書き・リンク・画像も使って見やすく答えてください。"
    )
    return await _run(system, payload.message, "chat")


@router.post("/summarize", response_model=AiOut)
async def summarize(payload: SummarizeIn) -> AiOut:
    """(b) 間接インジェクション用。外部文書を要約 → 文書内の指示にAIが従ってしまう。

    system prompt は「よくある実装」を再現: 要約結果をそのままWeb表示するため、
    元文書の画像やリンクは "動作する形で" 残す(コードブロックで囲まない)よう指示している。
    この"親切さ"こそが、毒入り文書の画像/リンクを通してしまう穴になる。
    """
    system = (
        "あなたは文書要約アシスタントです。与えられた文書を markdown で簡潔に要約してください。"
        "出力はそのままWebページに表示されます。元の文書にある画像やリンクは、"
        "コードブロックで囲まず、実際に表示・動作する形でそのまま残してください。"
    )
    user = f"次の文書を要約してください:\n\n---\n{payload.document}\n---"
    return await _run(system, user, "summarize")


@router.get("/health")
async def health() -> dict:
    """Gemini接続の診断。モックに落ちる原因を切り分けるために使う。
    例: curl http://localhost:8000/api/ai/health
    """
    api_key = _api_key()
    if not api_key:
        return {
            "key_set": False,
            "hint": "backend/.env に GEMINI_API_KEY=... を設定して uvicorn を再起動",
        }
    async with httpx.AsyncClient(timeout=25) as client:
        available = await _list_available(client, api_key)
    return {
        "key_set": True,
        "configured_models": _models(),
        "available_generateContent_models": available,
        "last_error": _last_error,
        "hint": (
            "configured_models が available に含まれているか確認。含まれていなければ "
            ".env に GEMINI_MODELS=<available の名前> を設定(自動検出でも動きます)。"
        ),
    }


# ---------------------------------------------------------------------------
# 「攻撃者の受信サーバ」を模したローカルendpoint。
# markdown画像 ![](/steal?c=...) が描画されるとブラウザが自動でここを取りに来る。
# → クエリに載った"盗んだデータ"がサーバログと /api/ai/steal-log に残る。
# これで「JS無しの情報漏洩(exfiltration)」を、外部に一切送らず体験できる。
# ---------------------------------------------------------------------------
_stolen: list[dict] = []

# 1x1 透明GIF
_PIXEL = bytes.fromhex(
    "47494638396101000100800000ffffff00000021f90401000000002c00000000"
    "0100010000020144003b"
)


@router.get("/steal")
async def steal(c: str = "", data: str = "") -> Response:
    payload = c or data or ""
    _stolen.append({"stolen": payload})
    # Windowsのcp932コンソールでは絵文字/日本語のprintが例外になるので握りつぶす。
    try:
        print(f"[attacker-server] received: {payload!r}")
    except Exception:
        pass
    return Response(content=_PIXEL, media_type="image/gif")


@router.get("/steal-log")
async def steal_log() -> dict:
    return {"count": len(_stolen), "entries": _stolen[-20:]}


@router.delete("/steal-log")
async def clear_steal_log() -> dict:
    _stolen.clear()
    return {"status": "cleared"}
