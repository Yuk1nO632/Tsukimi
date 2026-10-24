"""Tsukimi's first backend: anonymous browser sessions and persistent favorites."""

from contextlib import asynccontextmanager
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from database import Database

BACKEND_ROOT = Path(__file__).resolve().parent
COOKIE_NAME = "tsukimi_session"
SESSION_SECONDS = 30 * 24 * 60 * 60
logger = logging.getLogger("tsukimi")


class FavoriteList(BaseModel):
    favorite_ids: list[str]


def create_app(database_path: Path | None = None, catalog_path: Path | None = None,
               allowed_origins: set[str] | None = None) -> FastAPI:
    store = Database(database_path or Path(os.getenv("TSUKIMI_DATABASE", str(BACKEND_ROOT / "data/tsukimi.db"))))
    source = catalog_path or BACKEND_ROOT.parent / "catalog/catalog.json"
    origins = allowed_origins if allowed_origins is not None else set(
        os.getenv("TSUKIMI_ALLOWED_ORIGINS", "http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:8000,http://localhost:8000").split(",")
    )
    secure_cookie = os.getenv("TSUKIMI_COOKIE_SECURE", "0") == "1"

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        store.initialize()
        catalog = json.loads(source.read_text(encoding="utf-8"))
        application.state.anime_ids = {anime["id"] for anime in catalog["anime"]}
        yield

    application = FastAPI(title="Tsukimi API", version="0.1.0", lifespan=lifespan)

    @application.middleware("http")
    async def private_responses(request: Request, call_next):
        # Browser mutations must come from our frontend. CLI clients may omit Origin.
        if request.method in {"PUT", "DELETE", "POST", "PATCH"}:
            origin = request.headers.get("origin")
            if request.headers.get("sec-fetch-site") == "cross-site" or (origin is not None and origin not in origins):
                return JSONResponse(status_code=403, content={"detail": "该请求来源不被允许。"}, headers={"Cache-Control": "no-store"})
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(sqlite3.Error)
    async def unavailable_database(_request: Request, exception: sqlite3.Error):
        logger.error("SQLite operation failed: %s", type(exception).__name__)
        return JSONResponse(status_code=503, content={"detail": "收藏暂时无法读取或保存，请稍后重试。"})

    def current_session(request: Request) -> str | None:
        token = request.cookies.get(COOKIE_NAME, "")
        if re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is None:
            return None
        token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        return token_hash if store.session_exists(token_hash) else None

    def require_session(request: Request) -> str:
        session_id = current_session(request)
        if session_id is None:
            raise HTTPException(status_code=401, detail="追番会话已失效，请重新读取收藏后重试。")
        return session_id

    def favorites(session_id: str) -> FavoriteList:
        # A removed catalog item can stay in the DB but is hidden until it is available again.
        return FavoriteList(favorite_ids=[item for item in store.list_favorites(session_id) if item in application.state.anime_ids])

    @application.get("/api/health")
    def health():
        return {"status": "ok"}

    @application.get("/api/favorites", response_model=FavoriteList)
    def read_favorites(request: Request, response: Response):
        session_id = current_session(request)
        if session_id is None:
            token = secrets.token_urlsafe(32)
            session_id = hashlib.sha256(token.encode("ascii")).hexdigest()
            store.create_session(session_id, int(time.time()) + SESSION_SECONDS)
            response.set_cookie(COOKIE_NAME, token, max_age=SESSION_SECONDS, httponly=True,
                                secure=secure_cookie, samesite="lax", path="/api")
        return favorites(session_id)

    @application.put("/api/favorites/{anime_id}", response_model=FavoriteList)
    def save_favorite(anime_id: str, request: Request):
        session_id = require_session(request)
        if anime_id not in application.state.anime_ids:
            raise HTTPException(status_code=404, detail="这部番剧尚未收录。")
        store.set_favorite(session_id, anime_id, saved=True)
        return favorites(session_id)

    @application.delete("/api/favorites/{anime_id}", response_model=FavoriteList)
    def remove_favorite(anime_id: str, request: Request):
        session_id = require_session(request)
        if anime_id not in application.state.anime_ids:
            raise HTTPException(status_code=404, detail="这部番剧尚未收录。")
        store.set_favorite(session_id, anime_id, saved=False)
        return favorites(session_id)

    return application


app = create_app()
