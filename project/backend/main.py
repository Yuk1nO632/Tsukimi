"""Account/anonymous libraries, watch progress and aggregate playback."""

from contextlib import asynccontextmanager
import json
import logging
import os
from pathlib import Path
from typing import Literal
import sqlite3

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from sessions import Sessions, COOKIE_NAME
from accounts import create_account_router
from progress import create_progress_router

from database import Database
from catalog import BangumiClient, Catalog, CatalogError, create_catalog_router
from playback import create_playback_router
from source_errors import SourceError
from anich import AniChSource
from xifan import XifanSource

BACKEND_ROOT = Path(__file__).resolve().parent
load_dotenv(BACKEND_ROOT / ".env")
logger = logging.getLogger("tsukimi")


class FavoriteList(BaseModel):
    favorite_ids: list[str]


class CollectionUpdate(BaseModel):
    status: Literal["wish", "watching", "completed"]


def create_app(database_path: Path | None = None, catalog_path: Path | None = None,
               allowed_origins: set[str] | None = None, playback_source: AniChSource | None = None, metadata_source: BangumiClient | None = None, fallback_source: XifanSource | None = None) -> FastAPI:
    store = Database(database_path or Path(os.getenv("TSUKIMI_DATABASE", str(BACKEND_ROOT / "data/tsukimi.db"))))
    metadata_provider = metadata_source or BangumiClient()
    playback_provider = playback_source or AniChSource()
    fallback_provider = fallback_source or (XifanSource() if playback_source is None else None)
    source = catalog_path or BACKEND_ROOT.parent / "catalog/catalog.json"
    origins = allowed_origins if allowed_origins is not None else set(
        os.getenv("TSUKIMI_ALLOWED_ORIGINS", "http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:8000,http://localhost:8000").split(",")
    )
    secure_cookie = os.getenv("TSUKIMI_COOKIE_SECURE", "0") == "1"

    sessions = Sessions(store, secure_cookie)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        store.initialize()
        catalog = json.loads(source.read_text(encoding="utf-8"))
        application.state.anime_catalog = {anime["id"]: anime for anime in catalog["anime"]}
        application.state.anime_ids = set(application.state.anime_catalog)
        for anime in catalog["anime"]:
            store.cache_anime(anime, 0, seed=True)
        application.state.catalog = Catalog(store, metadata_provider)
        application.state.store = store
        try:
            yield
        finally:
            metadata_provider.close()
            playback_provider.close()
            if fallback_provider is not None:
                fallback_provider.close()

    application = FastAPI(title="Tsukimi API", version="0.5.0", lifespan=lifespan)


    application.include_router(create_catalog_router())

    @application.exception_handler(CatalogError)
    async def unavailable_catalog(_request: Request, error: CatalogError):
        return JSONResponse(status_code=error.status_code, content={"detail": str(error)})

    @application.exception_handler(SourceError)
    async def unavailable_source(_request: Request, error: SourceError):
        return JSONResponse(status_code=error.status_code, content={"detail": str(error)})

    @application.middleware("http")
    async def private_responses(request: Request, call_next):
        # Browser mutations must come from our frontend. CLI clients may omit Origin.
        if request.method in {"PUT", "DELETE", "POST", "PATCH"}:
            origin = request.headers.get("origin")
            if request.headers.get("sec-fetch-site") == "cross-site" or (origin is not None and origin not in origins):
                return JSONResponse(status_code=403, content={"detail": "该请求来源不被允许。"}, headers={"Cache-Control": "no-store"})
        if request.method in {"PUT", "DELETE", "POST", "PATCH"}:
            expected_scope = request.headers.get("x-tsukimi-scope")
            if expected_scope and expected_scope != session_scope(request):
                return JSONResponse(status_code=409, content={"detail": "登录身份已变化，请重新读取页面。"}, headers={"Cache-Control": "no-store"})
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(sqlite3.Error)
    async def unavailable_database(_request: Request, exception: sqlite3.Error):
        logger.error("SQLite operation failed: %s", type(exception).__name__)
        return JSONResponse(status_code=503, content={"detail": "追番记录暂时无法读取或保存，请稍后重试。"})

    current_session = sessions.current
    require_session = sessions.require
    ensure_session = sessions.ensure
    account_router, session_scope = create_account_router(store, sessions)
    application.include_router(account_router)
    application.include_router(create_progress_router(store, sessions, session_scope))

    def favorites(owner_id):
        return FavoriteList(favorite_ids=store.list_favorites(owner_id))

    @application.get("/api/health")
    def health():
        return {"status": "ok"}

    @application.get("/api/favorites", response_model=FavoriteList)
    def read_favorites(request: Request, response: Response):
        return favorites(ensure_session(request, response))

    def collection(owner_id):
        return {"items": store.list_collection(owner_id)}

    @application.get("/api/collection")
    def read_collection(request: Request, response: Response):
        return collection(ensure_session(request, response))

    @application.put("/api/collection/{anime_id}")
    def update_collection(anime_id: str, payload: CollectionUpdate, request: Request):
        owner_id = require_session(request)
        application.state.catalog.get(anime_id)
        store.set_collection_status(owner_id, anime_id, payload.status)
        return collection(owner_id)

    @application.delete("/api/collection/{anime_id}")
    def delete_collection(anime_id: str, request: Request):
        owner_id = require_session(request)
        store.set_favorite(owner_id, anime_id, saved=False)
        return collection(owner_id)

    @application.put("/api/favorites/{anime_id}", response_model=FavoriteList)
    def save_favorite(anime_id: str, request: Request):
        owner_id = require_session(request)
        application.state.catalog.get(anime_id)
        store.set_favorite(owner_id, anime_id, saved=True)
        return favorites(owner_id)

    @application.delete("/api/favorites/{anime_id}", response_model=FavoriteList)
    def remove_favorite(anime_id: str, request: Request):
        owner_id = require_session(request)
        if not store.cached_anime(anime_id):
            raise HTTPException(status_code=404, detail="这部番剧尚未收录。")
        store.set_favorite(owner_id, anime_id, saved=False)
        return favorites(owner_id)

    application.include_router(create_playback_router(playback_provider, current_session, require_session, fallback_provider))
    return application


app = create_app()
