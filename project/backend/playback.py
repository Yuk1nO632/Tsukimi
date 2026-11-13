"""Provider-scoped choices with automatic fallback, without caching signed URLs."""
import inspect

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from source_errors import SourceError


class SourceBinding(BaseModel):
    source_anime_id: int = Field(gt=0)


def create_playback_router(provider, current_session, require_session, fallback_provider=None):
    router = APIRouter(prefix="/api")
    providers = {item.name: item for item in (provider, fallback_provider) if item is not None}

    def get_provider(name):
        if name not in providers:
            raise HTTPException(404, "播放来源不存在。")
        return providers[name]

    @router.get("/sources/{source_provider}/search")
    def search(source_provider: str, q: str = Query(min_length=1, max_length=80)):
        selected = get_provider(source_provider)
        query = q.strip()
        if not query:
            raise HTTPException(status_code=400, detail="请输入来源搜索关键词。")
        return {"provider": selected.name, "items": selected.search(query)}

    @router.put("/sources/{source_provider}/bindings/{anime_id}")
    def remember(source_provider: str, anime_id: str, payload: SourceBinding, request: Request):
        selected = get_provider(source_provider)
        owner_id = require_session(request)
        anime = request.app.state.catalog.get(anime_id)
        selected.validate_binding(anime, payload.source_anime_id)
        request.app.state.store.save_source_binding(
            f"{selected.name}:{anime_id}", payload.source_anime_id, owner_id, preferred_provider=selected.name,
        )
        return {"anime_id": anime_id, "source_anime_id": payload.source_anime_id, "provider": selected.name}

    def resolve(selected, anime, request, episode, source_id, line_id):
        store = request.app.state.store
        key = f"{selected.name}:{anime['id']}"
        saved_id, kind = store.source_binding(key, current_session(request))
        if source_id:
            saved_id, kind = source_id, "explicit"
        if saved_id is None:
            saved_id, candidates = selected.discover(anime)
            if saved_id is None:
                return {"status": "unmatched", "provider": selected.name, "candidates": candidates,
                        "message": "未能唯一确认对应作品，请从候选中选择一次。" if candidates else "暂未找到对应来源，可以尝试别名或稍后重试。"}
            store.save_source_binding(key, saved_id)
            kind = "automatic"
        try:
            selected.validate_binding(anime, saved_id)
            extra = {"anime": anime} if "anime" in inspect.signature(selected.resolve).parameters else {}
            return {**selected.resolve(saved_id, episode, line_id, **extra), "match_kind": kind}
        except SourceError as error:
            if kind == "automatic" and error.status_code in {404, 409} and line_id is None:
                store.forget_auto_source(key)
            raise

    @router.get("/playback/{anime_id}")
    def playback(anime_id: str, request: Request, episode: int = Query(default=1, ge=1),
                 source_anime_id: int | None = Query(default=None, ge=1),
                 line_id: int | None = Query(default=None, ge=1),
                 source_provider: str | None = Query(default=None, max_length=20)):
        selected = providers.get(source_provider)
        if selected is None:
            # Unscoped legacy numeric IDs cannot identify a provider safely.
            source_anime_id = line_id = None
            preference = request.app.state.store.preferred_playback_provider(anime_id, current_session(request))
            selected = providers.get(preference)
        anime = request.app.state.catalog.get(anime_id)
        if anime["episodes"] > 0 and episode > anime["episodes"]:
            raise HTTPException(status_code=404, detail="这部番剧没有所选集数。")
        order = list(providers.values())
        if selected:
            order.remove(selected)
            order.insert(0, selected)
        results, errors = [], []
        enriched = False
        for item in order:
            try:
                result = resolve(item, anime, request, episode,
                                 source_anime_id if item is selected else None,
                                 line_id if item is selected else None)
                if not enriched and not anime.get("detailComplete") and (
                    result["status"] == "unavailable" and result.get("reason") == "unverified_resources"
                ):
                    enriched = True
                    refreshed = request.app.state.catalog.get(anime_id, enrich=True)
                    if refreshed.get("detailComplete") or refreshed.get("aliases") != anime.get("aliases"):
                        anime = refreshed
                        result = resolve(item, anime, request, episode,
                                         source_anime_id if item is selected else None,
                                         line_id if item is selected else None)
                if result["status"] == "ready":
                    if item is not order[0]:
                        result["fallback_from"] = order[0].name
                        result["fallback_message"] = str(errors[0]) if errors else results[0].get("message", "")
                    return result
                results.append(result)
            except SourceError as error:
                if error.status_code == 409 and source_anime_id and item is selected:
                    raise
                errors.append(error)
        if results:
            return next((result for result in results if result.get("source_anime_id") or result.get("candidates")), results[-1])
        raise errors[-1]

    return router
