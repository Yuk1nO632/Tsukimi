"""Resolve a source automatically; remember explicit browser choices without storing signed URLs."""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from matching import discover_source
from xifan import SourceError, XifanSource


class SourceBinding(BaseModel):
    source_anime_id: int = Field(gt=0)


def create_playback_router(provider: XifanSource, current_session, require_session):
    router = APIRouter(prefix="/api")

    @router.get("/sources/xifan/search")
    def search(q: str = Query(min_length=1, max_length=80)):
        query = q.strip()
        if not query:
            raise HTTPException(status_code=400, detail="请输入来源搜索关键词。")
        return {"provider": "xifan", "items": provider.search(query)}

    @router.put("/sources/xifan/bindings/{anime_id}")
    def remember(anime_id: str, payload: SourceBinding, request: Request):
        session_id = require_session(request)
        request.app.state.catalog.get(anime_id)
        provider.detail(payload.source_anime_id)
        request.app.state.store.save_source_binding(anime_id, payload.source_anime_id, session_id)
        return {"anime_id": anime_id, "source_anime_id": payload.source_anime_id}

    @router.get("/playback/{anime_id}")
    def playback(anime_id: str, request: Request, episode: int = Query(default=1, ge=1),
                 source_anime_id: int | None = Query(default=None, ge=1),
                 line_id: int | None = Query(default=None, ge=1)):
        anime = request.app.state.catalog.get(anime_id)
        if anime["episodes"] > 0 and episode > anime["episodes"]:
            raise HTTPException(status_code=404, detail="这部番剧没有所选集数。")
        store = request.app.state.store
        session_id = current_session(request)
        source_id, kind = store.source_binding(anime_id, session_id)
        if source_anime_id:
            source_id, kind = source_anime_id, "explicit"
        elif kind != "saved" and anime_id in request.app.state.xifan_bindings:
            source_id, kind = request.app.state.xifan_bindings[anime_id], "default"
        if source_id is None:
            source_id, candidates = discover_source(anime, provider)
            if source_id is None:
                return {"status": "unmatched", "provider": "xifan", "candidates": candidates,
                        "message": "未能唯一确认对应作品，请从候选中选择一次。" if candidates else "暂未找到对应来源，可以尝试别名或稍后重试。"}
            store.save_source_binding(anime_id, source_id)
            kind = "automatic"
        try:
            return {**provider.resolve(source_id, episode, line_id), "match_kind": kind}
        except SourceError as error:
            if kind == "automatic" and error.status_code == 404 and line_id is None:
                store.forget_auto_source(anime_id)
            raise

    return router
