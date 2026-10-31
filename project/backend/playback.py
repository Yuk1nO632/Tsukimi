"""Resolve a source automatically; remember explicit browser choices without storing signed URLs."""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from matching import discover_source
from xifan import SourceError


class SourceBinding(BaseModel):
    source_anime_id: int = Field(gt=0)


def create_playback_router(provider, current_session, require_session):
    router = APIRouter(prefix="/api")
    provider_name = getattr(provider, "name", "xifan")

    def binding_key(anime_id):
        # Existing unprefixed IDs belong to Xifan; never reuse them for AniCh.
        return anime_id if provider_name == "xifan" else f"{provider_name}:{anime_id}"

    @router.get(f"/sources/{provider_name}/search")
    def search(q: str = Query(min_length=1, max_length=80)):
        query = q.strip()
        if not query:
            raise HTTPException(status_code=400, detail="请输入来源搜索关键词。")
        return {"provider": provider_name, "items": provider.search(query)}

    @router.put(f"/sources/{provider_name}/bindings/{{anime_id}}")
    def remember(anime_id: str, payload: SourceBinding, request: Request):
        session_id = require_session(request)
        anime = request.app.state.catalog.get(anime_id)
        provider.detail(payload.source_anime_id)
        if hasattr(provider, "validate_binding"):
            provider.validate_binding(anime, payload.source_anime_id)
        request.app.state.store.save_source_binding(binding_key(anime_id), payload.source_anime_id, session_id)
        return {"anime_id": anime_id, "source_anime_id": payload.source_anime_id}

    @router.get("/playback/{anime_id}")
    def playback(anime_id: str, request: Request, episode: int = Query(default=1, ge=1),
                 source_anime_id: int | None = Query(default=None, ge=1),
                 line_id: int | None = Query(default=None, ge=1),
                 source_provider: str | None = Query(default=None, max_length=20)):
        if provider_name == "anich" and source_provider != "anich":
            # Legacy URLs contain Xifan IDs with the same numeric shape.
            source_anime_id = line_id = None
        anime = request.app.state.catalog.get(anime_id)
        if anime["episodes"] > 0 and episode > anime["episodes"]:
            raise HTTPException(status_code=404, detail="这部番剧没有所选集数。")
        store = request.app.state.store
        session_id = current_session(request)
        source_id, kind = store.source_binding(binding_key(anime_id), session_id)
        if source_anime_id:
            source_id, kind = source_anime_id, "explicit"
        elif provider_name == "xifan" and kind != "saved" and anime_id in request.app.state.xifan_bindings:
            source_id, kind = request.app.state.xifan_bindings[anime_id], "default"
        if source_id is None:
            source_id, candidates = provider.discover(anime) if hasattr(provider, "discover") else discover_source(anime, provider)
            if source_id is None:
                return {"status": "unmatched", "provider": provider_name, "candidates": candidates,
                        "message": "未能唯一确认对应作品，请从候选中选择一次。" if candidates else "暂未找到对应来源，可以尝试别名或稍后重试。"}
            store.save_source_binding(binding_key(anime_id), source_id)
            kind = "automatic"
        try:
            if hasattr(provider, "validate_binding"):
                provider.validate_binding(anime, source_id)
            return {**provider.resolve(source_id, episode, line_id), "match_kind": kind}
        except SourceError as error:
            if kind == "automatic" and error.status_code in {404, 409} and line_id is None:
                store.forget_auto_source(binding_key(anime_id))
            raise

    return router
