"""Versioned last-watched position, isolated by server-resolved ownership."""

import time
from typing import Literal
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


class ProgressInput(BaseModel):
    episode: int = Field(ge=1, le=100000)
    position: float = Field(ge=0, le=604800, allow_inf_nan=False)
    duration: float = Field(gt=0, le=604800, allow_inf_nan=False)
    source_provider: Literal["anich", "xifan"] = "anich"
    source_id: int | None = Field(default=None, gt=0)
    line_id: int | None = Field(default=None, gt=0)
    completed: bool = False
    revision: int = Field(ge=0)
    operation_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{16,80}$")
    scope: str = Field(min_length=64, max_length=64)


class ProgressDeleteInput(BaseModel):
    revision: int = Field(ge=0)
    operation_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{16,80}$")
    scope: str = Field(min_length=64, max_length=64)


def create_progress_router(store, sessions, scope):
    router = APIRouter(prefix="/api/progress")

    @router.get("")
    def list_progress(request: Request, response: Response):
        return {"items": store.list_progress(sessions.ensure(request, response))}

    @router.get("/{anime_id}")
    def read_progress(anime_id: str, request: Request, response: Response):
        return {"item": store.progress(sessions.ensure(request, response), anime_id)}

    @router.put("/{anime_id}")
    def save_progress(anime_id: str, payload: ProgressInput, request: Request):
        owner = sessions.require(request)
        if payload.scope != scope(request):
            raise HTTPException(409, "登录身份已变化，请重新读取观看进度。")
        anime = request.app.state.catalog.get(anime_id)
        if anime["episodes"] > 0 and payload.episode > anime["episodes"]:
            raise HTTPException(400, "集数超出番剧范围。")
        if payload.position > payload.duration + 1:
            raise HTTPException(400, "观看位置超出视频时长。")
        with store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if sessions.current(request) != owner:
                raise HTTPException(401, "会话已失效，请重新登录。")
            current = store.progress_row(connection, owner, anime_id)
            if current and current["operation_id"] == payload.operation_id:
                return {"item": current}
            revision = current["revision"] if current else 0
            if revision != payload.revision:
                return JSONResponse(
                    status_code=409,
                    content={"detail": "另一设备已更新观看进度。", "item": current},
                )
            connection.execute(
                """INSERT INTO watch_progress
                (owner_id, anime_id, episode, position, duration, source_id, line_id, completed, revision, updated_at, operation_id, source_provider)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(owner_id, anime_id) DO UPDATE SET
                episode=excluded.episode, position=excluded.position, duration=excluded.duration,
                source_id=excluded.source_id, line_id=excluded.line_id, source_provider=excluded.source_provider, completed=excluded.completed,
                revision=excluded.revision, updated_at=excluded.updated_at, operation_id=excluded.operation_id""",
                (
                    owner,
                    anime_id,
                    payload.episode,
                    min(payload.position, payload.duration),
                    payload.duration,
                    payload.source_id,
                    payload.line_id,
                    int(payload.completed),
                    revision + 1,
                    time.time_ns() // 1000000,
                    payload.operation_id,
                    payload.source_provider,
                ),
            )
            return {"item": store.progress_row(connection, owner, anime_id)}

    @router.delete("/{anime_id}")
    def delete_progress(anime_id: str, payload: ProgressDeleteInput, request: Request):
        owner = sessions.require(request)
        if payload.scope != scope(request):
            raise HTTPException(409, "登录身份已变化，请重新读取观看进度。")
        with store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if sessions.current(request) != owner:
                raise HTTPException(401, "会话已失效，请重新登录。")
            current = store.progress_row(connection, owner, anime_id)
            if current and current["operation_id"] == payload.operation_id:
                return {"item": current}
            revision = current["revision"] if current else 0
            if revision != payload.revision:
                return JSONResponse(
                    status_code=409,
                    content={"detail": "观看记录已变化，请刷新后再删除。", "item": current},
                )
            if current is None:
                return {"item": None}
            # Saves require a positive duration. Keep a zero-duration marker and
            # advance its revision so an old player cannot recreate deleted progress.
            connection.execute(
                """UPDATE watch_progress SET
                episode=1, position=0, duration=0, source_id=NULL, line_id=NULL,
                source_provider='anich', completed=0, revision=?, updated_at=?, operation_id=?
                WHERE owner_id=? AND anime_id=?""",
                (revision + 1, time.time_ns() // 1000000, payload.operation_id, owner, anime_id),
            )
            return {"item": store.progress_row(connection, owner, anime_id)}

    return router
