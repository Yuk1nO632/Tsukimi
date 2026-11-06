"""Email accounts, bounded OTP verification and explicit anonymous import."""

import hashlib
import hmac
import re
import secrets
import time
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from pwdlib import PasswordHash

PASSWORDS = PasswordHash.recommended()
DUMMY_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))


class EmailInput(BaseModel):
    email: str = Field(min_length=3, max_length=254)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(
            r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}",
            value,
        ):
            raise ValueError("请输入有效的邮箱地址")
        return value


class CodeInput(EmailInput):
    purpose: Literal["register", "reset"]


class LoginInput(EmailInput):
    password: str = Field(min_length=10, max_length=128)


class RegisterInput(LoginInput):
    code: str = Field(pattern=r"^[0-9]{6}$")
    nickname: str = Field(min_length=1, max_length=30)

    @field_validator("nickname")
    @classmethod
    def nickname_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("请填写昵称")
        return value


class ResetInput(LoginInput):
    code: str = Field(pattern=r"^[0-9]{6}$")


class PasswordInput(BaseModel):
    current_password: str = Field(min_length=10, max_length=128)
    password: str = Field(min_length=10, max_length=128)


class ImportInput(BaseModel):
    action: Literal["merge", "skip"]


def scope_value(token):
    return hashlib.sha256(f"scope:{token}".encode()).hexdigest() if token else None


def create_account_router(store, sessions, mailer):
    router = APIRouter(prefix="/api/account")

    def code_digest(email, purpose, code):
        with store.connect() as connection:
            row = connection.execute(
                "SELECT value FROM app_secrets WHERE name = 'otp'"
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT OR IGNORE INTO app_secrets VALUES ('otp', ?)",
                    (secrets.token_hex(32),),
                )
                row = connection.execute(
                    "SELECT value FROM app_secrets WHERE name = 'otp'"
                ).fetchone()
        return hmac.new(
            row[0].encode(), f"{email}:{purpose}:{code}".encode(), hashlib.sha256
        ).hexdigest()

    def scope(request):
        return scope_value(sessions.token_hash(request))

    def limit(key, maximum, seconds):
        now = int(time.time())
        bucket = hashlib.sha256(key.encode()).hexdigest()
        with store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM rate_limits WHERE started_at < ?", (now - 86400,)
            )
            row = connection.execute(
                "SELECT started_at, count FROM rate_limits WHERE bucket = ?", (bucket,)
            ).fetchone()
            started, count = row if row and row[0] > now - seconds else (now, 0)
            allowed = count < maximum
            if allowed:
                connection.execute(
                    "INSERT OR REPLACE INTO rate_limits VALUES (?, ?, ?)",
                    (bucket, started, count + 1),
                )
        if not allowed:
            raise HTTPException(429, "操作过于频繁，请稍后再试。")

    def guard(request, email, operation):
        ip = request.client.host if request.client else "unknown"
        limit(f"{operation}:ip:{ip}", 30, 3600)
        limit(
            f"{operation}:email:{email}",
            8 if operation == "code" else 10,
            3600 if operation == "code" else 900,
        )

    def state(owner, token):
        with store.connect() as connection:
            pending = connection.execute(
                "SELECT 1 FROM pending_imports WHERE token_hash = ?", (token,)
            ).fetchone()
        return {
            "user": store.user(owner),
            "scope": scope_value(token),
            "pending_import": bool(pending),
            "mail_ready": mailer.ready,
            "mail_mode": mailer.mode,
        }

    def verified(connection, email, purpose, digest):
        row = connection.execute(
            "SELECT digest, expires_at, attempts FROM email_codes WHERE email = ? AND purpose = ?",
            (email, purpose),
        ).fetchone()
        if not row or row[1] <= int(time.time()) or row[2] >= 5:
            return False
        valid = hmac.compare_digest(row[0], digest)
        connection.execute(
            "UPDATE email_codes SET attempts = attempts + 1 WHERE email = ? AND purpose = ?",
            (email, purpose),
        )
        return valid

    def login_session(request, response, user_id, connection):
        old_token = sessions.token_hash(request)
        old_owner = sessions.current(request)
        anonymous = old_owner and store.user(old_owner) is None
        _, new_token = sessions.issue(response, user_id, connection)
        if anonymous:
            count = sum(
                connection.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE owner_id = ?", (old_owner,)
                ).fetchone()[0]
                for table in (
                    "owned_favorites",
                    "watch_progress",
                    "owned_source_bindings",
                )
            )
            if count:
                connection.execute(
                    "INSERT INTO pending_imports VALUES (?, ?)", (new_token, old_owner)
                )
        if old_token:
            connection.execute(
                "DELETE FROM sessions WHERE token_hash = ?", (old_token,)
            )
        return new_token

    @router.get("")
    def read_account(request: Request, response: Response):
        token = sessions.token_hash(request)
        if token:
            return state(sessions.current(request), token)
        owner, token = sessions.issue(response)
        return state(owner, token)

    @router.post("/code")
    def send_code(payload: CodeInput, request: Request):
        if not mailer.ready:
            raise HTTPException(
                503, "邮件服务尚未配置，请按账号指南启用本地开发邮箱或腾讯云 SES。"
            )
        if mailer.mode == "file" and (
            request.client is None
            or request.client.host not in {"127.0.0.1", "::1", "testclient"}
        ):
            raise HTTPException(403, "开发邮箱仅供本机验收。")
        guard(request, payload.email, "code")
        now = int(time.time())
        code = f"{secrets.randbelow(1000000):06d}"
        digest = code_digest(payload.email, payload.purpose, code)
        generation = secrets.token_hex(16)
        with store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute(
                "SELECT sent_at FROM email_codes WHERE email = ? AND purpose = ?",
                (payload.email, payload.purpose),
            ).fetchone()
            if previous and previous[0] > now - 60:
                raise HTTPException(429, "请间隔 60 秒再发送验证码。")
            exists = (
                connection.execute(
                    "SELECT 1 FROM users WHERE email = ?", (payload.email,)
                ).fetchone()
                is not None
            )
            connection.execute(
                "INSERT OR REPLACE INTO email_codes VALUES (?, ?, ?, ?, 0, ?, ?)",
                (payload.email, payload.purpose, digest, now + 300, now, generation),
            )
        deliver = (payload.purpose == "register" and not exists) or (
            payload.purpose == "reset" and exists
        )
        if deliver:
            try:
                mailer.send(payload.email, payload.purpose, code)
            except Exception:
                with store.connect() as connection:
                    connection.execute(
                        "DELETE FROM email_codes WHERE email = ? AND purpose = ? AND generation = ?",
                        (payload.email, payload.purpose, generation),
                    )
                raise
        return {
            "message": "如果该邮箱符合操作条件，验证码将发送至邮箱。",
            "retry_after": 60,
        }

    @router.post("/register")
    def register(payload: RegisterInput, request: Request, response: Response):
        guard(request, payload.email, "register")
        digest = code_digest(payload.email, "register", payload.code)
        password_hash = PASSWORDS.hash(payload.password)
        owner = secrets.token_hex(16)
        with store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            valid = verified(connection, payload.email, "register", digest)
            exists = connection.execute(
                "SELECT 1 FROM users WHERE email = ?", (payload.email,)
            ).fetchone()
            success = valid and not exists
            if success:
                connection.execute("INSERT INTO owners VALUES (?)", (owner,))
                connection.execute(
                    "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                    (
                        owner,
                        payload.email,
                        payload.nickname,
                        password_hash,
                        int(time.time()),
                    ),
                )
                connection.execute(
                    "DELETE FROM email_codes WHERE email = ? AND purpose = 'register'",
                    (payload.email,),
                )
                token = login_session(request, response, owner, connection)
        if not success:
            raise HTTPException(400, "注册未完成，请确认邮箱、验证码及账号是否已注册。")
        return state(owner, token)

    @router.post("/login")
    def login(payload: LoginInput, request: Request, response: Response):
        guard(request, payload.email, "login")
        with store.connect() as connection:
            row = connection.execute(
                "SELECT id, password_hash FROM users WHERE email = ?", (payload.email,)
            ).fetchone()
        valid = PASSWORDS.verify(payload.password, row[1] if row else DUMMY_HASH)
        if not valid or not row:
            raise HTTPException(401, "邮箱或密码有误。")
        with store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if (
                connection.execute(
                    "SELECT 1 FROM users WHERE id = ? AND password_hash = ?", row
                ).fetchone()
                is None
            ):
                raise HTTPException(409, "密码已更新，请重新登录。")
            token = login_session(request, response, row[0], connection)
        return state(row[0], token)

    @router.post("/logout")
    def logout(request: Request, response: Response):
        token = sessions.token_hash(request)
        with store.connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token,))
        response.delete_cookie(
            "tsukimi_session",
            path="/api",
            httponly=True,
            secure=sessions.secure,
            samesite="lax",
        )
        return {"message": "已退出当前设备。"}

    @router.post("/reset-password")
    def reset_password(payload: ResetInput, request: Request):
        guard(request, payload.email, "reset")
        digest = code_digest(payload.email, "reset", payload.code)
        password_hash = PASSWORDS.hash(payload.password)
        with store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            valid = verified(connection, payload.email, "reset", digest)
            row = connection.execute(
                "SELECT id FROM users WHERE email = ?", (payload.email,)
            ).fetchone()
            success = valid and row is not None
            if success:
                connection.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (password_hash, row[0]),
                )
                connection.execute(
                    "DELETE FROM email_codes WHERE email = ?", (payload.email,)
                )
                connection.execute("DELETE FROM sessions WHERE owner_id = ?", (row[0],))
        if not success:
            raise HTTPException(400, "邮箱或验证码有误，或验证码已过期。")
        return {"message": "密码已重置，请使用新密码登录。"}

    @router.post("/password")
    def change_password(payload: PasswordInput, request: Request):
        user = sessions.account(request)
        guard(request, user["email"], "password")
        with store.connect() as connection:
            old_hash = connection.execute(
                "SELECT password_hash FROM users WHERE id = ?", (user["id"],)
            ).fetchone()[0]
        if not PASSWORDS.verify(payload.current_password, old_hash):
            raise HTTPException(400, "当前密码有误。")
        new_hash = PASSWORDS.hash(payload.password)
        with store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                "UPDATE users SET password_hash = ? WHERE id = ? AND password_hash = ?",
                (new_hash, user["id"], old_hash),
            ).rowcount
            if not changed:
                raise HTTPException(409, "密码已更新，请重新登录。")
            connection.execute("DELETE FROM sessions WHERE owner_id = ?", (user["id"],))
            connection.execute(
                "DELETE FROM email_codes WHERE email = ?", (user["email"],)
            )
        return {"message": "密码已修改，请重新登录。"}

    @router.post("/import")
    def import_anonymous(payload: ImportInput, request: Request):
        user = sessions.account(request)
        token = sessions.token_hash(request)
        with store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if sessions.current(request) != user["id"]:
                raise HTTPException(401, "会话已失效，请重新登录。")
            row = connection.execute(
                "SELECT anonymous_owner FROM pending_imports WHERE token_hash = ?",
                (token,),
            ).fetchone()
            if row and payload.action == "merge":
                for table in (
                    "owned_favorites",
                    "owned_source_bindings",
                    "watch_progress",
                ):
                    columns = [
                        column[1]
                        for column in connection.execute(f"PRAGMA table_info({table})")
                        if column[1] != "owner_id"
                    ]
                    names = ", ".join(columns)
                    connection.execute(
                        f"INSERT OR IGNORE INTO {table} (owner_id, {names}) SELECT ?, {names} FROM {table} WHERE owner_id = ?",
                        (user["id"], row[0]),
                    )
            connection.execute(
                "DELETE FROM pending_imports WHERE token_hash = ?", (token,)
            )
        return state(user["id"], token)

    return router, scope
