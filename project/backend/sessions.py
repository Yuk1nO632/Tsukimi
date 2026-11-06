"""Device cookies resolve to a stable anonymous or account data owner."""

import hashlib
import re
import secrets
import time
from fastapi import HTTPException

COOKIE_NAME = "tsukimi_session"
SESSION_SECONDS = 30 * 24 * 60 * 60


class Sessions:
    def __init__(self, store, secure=False):
        self.store = store
        self.secure = secure

    def token_hash(self, request):
        token = request.cookies.get(COOKIE_NAME, "")
        if re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is None:
            return None
        digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        return digest if self.store.session_exists(digest) else None

    def current(self, request):
        digest = self.token_hash(request)
        return self.store.session_owner(digest) if digest else None

    def require(self, request):
        owner = self.current(request)
        if owner is None:
            raise HTTPException(401, "会话已失效，请重新读取页面后重试。")
        return owner

    def ensure(self, request, response):
        return self.current(request) or self.issue(response)[0]

    def issue(self, response, owner=None, connection=None):
        token = secrets.token_urlsafe(32)
        digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        owner = owner or digest
        expiry = int(time.time()) + SESSION_SECONDS
        if connection is None:
            self.store.create_session(digest, expiry, owner)
        else:
            connection.execute(
                "INSERT INTO sessions (token_hash, expires_at, owner_id) VALUES (?, ?, ?)",
                (digest, expiry, owner),
            )
        response.set_cookie(
            COOKIE_NAME,
            token,
            max_age=SESSION_SECONDS,
            httponly=True,
            secure=self.secure,
            samesite="lax",
            path="/api",
        )
        return owner, digest

    def account(self, request):
        user = self.store.user(self.require(request))
        if user is None:
            raise HTTPException(401, "请先登录账号。")
        return user
