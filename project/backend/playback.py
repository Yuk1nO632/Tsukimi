"""Playback discovery stays separate from favorites and public Bangumi metadata."""

from fastapi import APIRouter, HTTPException, Query, Request

from xifan import XifanSource


def create_playback_router(provider: XifanSource):
    router = APIRouter(prefix="/api")

    @router.get("/sources/xifan/search")
    def search(q: str = Query(min_length=1, max_length=80)):
        query = q.strip()
        if not query:
            raise HTTPException(status_code=400, detail="请输入来源搜索关键词。")
        return {"provider": "xifan", "items": provider.search(query)}

    @router.get("/playback/{anime_id}")
    def playback(anime_id: str, request: Request, episode: int = Query(default=1, ge=1),
                 source_anime_id: int | None = Query(default=None, ge=1),
                 line_id: int | None = Query(default=None, ge=1)):
        anime = request.app.state.anime_catalog.get(anime_id)
        if anime is None:
            raise HTTPException(status_code=404, detail="这部番剧尚未收录。")
        if episode > anime["episodes"]:
            raise HTTPException(status_code=404, detail="这部番剧没有所选集数。")
        source_id = source_anime_id or request.app.state.xifan_bindings.get(anime_id)
        if source_id is None:
            return {"status": "unmatched", "provider": "xifan", "message": "先匹配稀饭动漫中的对应作品，再开始播放。"}
        return provider.resolve(source_id, episode, line_id)

    return router
