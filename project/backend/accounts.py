"""Username accounts and password recovery with three hashed security answers."""

import hashlib
import json
import re
import secrets
import time
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from pwdlib import PasswordHash

PASSWORDS = PasswordHash.recommended()
DUMMY_HASH = PASSWORDS.hash(secrets.token_urlsafe(32))


def answer_text(value):
    import unicodedata

    return unicodedata.normalize("NFKC", value).strip().casefold()


class UsernameInput(BaseModel):
    username: str = Field(min_length=3, max_length=254)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value):
        return value.strip().lower()


class LoginInput(UsernameInput):
    password: str = Field(min_length=10, max_length=128)


class SecurityQuestion(BaseModel):
    question: str = Field(min_length=4, max_length=100)
    answer: str = Field(min_length=6, max_length=128)

    @field_validator("question")
    @classmethod
    def trim_question(cls, value):
        value = value.strip()
        if len(value) < 4:
            raise ValueError("问题至少需要 4 个字符")
        return value

    @field_validator("answer")
    @classmethod
    def normalize_answer(cls, value):
        value = answer_text(value)
        if len(value) < 6:
            raise ValueError("密保答案至少需要 6 个字符")
        return value


class SecuritySetup(BaseModel):
    questions: list[SecurityQuestion] = Field(min_length=3, max_length=3)

    @field_validator("questions")
    @classmethod
    def distinct_questions(cls, value):
        if (
            len({item.question.casefold() for item in value}) != 3
            or len({item.answer for item in value}) != 3
        ):
            raise ValueError("请设置三个不同的问题和答案")
        return value


class RegisterInput(LoginInput, SecuritySetup):
    nickname: str = Field(min_length=1, max_length=30)

    @field_validator("username")
    @classmethod
    def new_username(cls, value):
        if not re.fullmatch(r"[a-z0-9_]{4,32}", value):
            raise ValueError("账号名使用 4–32 位英文字母、数字或下划线")
        return value

    @field_validator("nickname")
    @classmethod
    def nickname_text(cls, value):
        if not value.strip():
            raise ValueError("请填写昵称")
        return value.strip()


class ResetInput(LoginInput):
    challenge: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    answers: list[str] = Field(min_length=3, max_length=3)

    @field_validator("answers")
    @classmethod
    def normalize_answers(cls, values):
        if any(not 6 <= len(answer_text(value)) <= 128 for value in values):
            raise ValueError("密保答案长度应为 6–128 个字符")
        return [answer_text(value) for value in values]


class PasswordInput(BaseModel):
    current_password: str = Field(min_length=10, max_length=128)
    password: str = Field(min_length=10, max_length=128)


class SecurityUpdate(SecuritySetup):
    current_password: str = Field(min_length=10, max_length=128)


class ImportInput(BaseModel):
    action: Literal["merge", "skip"]


def scope_value(token):
    return hashlib.sha256(f"scope:{token}".encode()).hexdigest() if token else None


def create_account_router(store, sessions):
    router = APIRouter(prefix="/api/account")

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

    def guard(request, username, operation):
        ip = request.client.host if request.client else "unknown"
        limit(f"{operation}:ip:{ip}", 30, 3600)
        limit(
            f"{operation}:username:{username}",
            10,
            900,
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
        }

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
                    "playback_preferences",
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

    def encoded_questions(questions):
        return json.dumps(
            [
                {"question": item.question, "hash": PASSWORDS.hash(item.answer)}
                for item in questions
            ],
            ensure_ascii=False,
        )

    @router.post("/register")
    def register(payload: RegisterInput, request: Request, response: Response):
        guard(request, payload.username, "register")
        password_hash = PASSWORDS.hash(payload.password)
        security_json = encoded_questions(payload.questions)
        owner = secrets.token_hex(16)
        with store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            exists = connection.execute(
                "SELECT 1 FROM users WHERE username = ?", (payload.username,)
            ).fetchone()
            if exists:
                raise HTTPException(409, "该账号名已被使用，请换一个。")
            connection.execute("INSERT INTO owners VALUES (?)", (owner,))
            # Legacy email is NOT NULL/UNIQUE. This reserved internal value represents an unbound account.
            connection.execute(
                """INSERT INTO users (id, email, nickname, password_hash, created_at, username, security_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    owner,
                    f"unbound:{owner}",
                    payload.nickname,
                    password_hash,
                    int(time.time()),
                    payload.username,
                    security_json,
                ),
            )
            token = login_session(request, response, owner, connection)
        return state(owner, token)

    def credential_version(row):
        return hashlib.sha256((row[1] + row[2]).encode()).hexdigest()

    @router.post("/recovery")
    def recovery(payload: UsernameInput, request: Request):
        guard(request, payload.username, "recovery")
        session_hash = sessions.token_hash(request)
        if not session_hash:
            raise HTTPException(401, "请刷新页面后重试。")
        token = secrets.token_urlsafe(32)
        with store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM recovery_challenges WHERE expires_at < ?",
                (int(time.time()),),
            )
            row = connection.execute(
                "SELECT id, password_hash, security_json FROM users WHERE username = ?",
                (payload.username,),
            ).fetchone()
            questions = json.loads(row[2]) if row else []
            prompts = [item["question"] for item in questions] or [
                "注册时设置的第一个密保问题？",
                "注册时设置的第二个密保问题？",
                "注册时设置的第三个密保问题？",
            ]
            connection.execute(
                "INSERT INTO recovery_challenges VALUES (?, ?, ?, ?, ?, ?, 0)",
                (
                    hashlib.sha256(token.encode()).hexdigest(),
                    session_hash,
                    payload.username,
                    row[0] if row and questions else None,
                    credential_version(row) if row else "",
                    int(time.time()) + 300,
                ),
            )
        return {"challenge": token, "questions": prompts, "expires_in": 300}

    @router.post("/login")
    def login(payload: LoginInput, request: Request, response: Response):
        guard(request, payload.username, "login")
        with store.connect() as connection:
            row = connection.execute(
                "SELECT id, password_hash FROM users WHERE username = ?",
                (payload.username,),
            ).fetchone()
        valid = PASSWORDS.verify(payload.password, row[1] if row else DUMMY_HASH)
        if not valid or not row:
            raise HTTPException(401, "账号名或密码有误。")
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
        guard(request, payload.username, "reset")
        token_hash = hashlib.sha256(payload.challenge.encode()).hexdigest()
        with store.connect() as connection:
            challenge = connection.execute(
                "SELECT user_id, credential_version, expires_at, attempts, session_hash, username FROM recovery_challenges WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()
            row = connection.execute(
                "SELECT id, password_hash, security_json FROM users WHERE username = ?",
                (payload.username,),
            ).fetchone()
        valid = bool(
            challenge
            and row
            and challenge[0] == row[0]
            and challenge[1] == credential_version(row)
            and challenge[2] > time.time()
            and challenge[3] < 5
            and challenge[4] == sessions.token_hash(request)
            and challenge[5] == payload.username
        )
        questions = json.loads(row[2]) if valid else []
        matches = [
            PASSWORDS.verify(
                answer, questions[index]["hash"] if len(questions) == 3 else DUMMY_HASH
            )
            for index, answer in enumerate(payload.answers)
        ]
        new_hash = PASSWORDS.hash(payload.password) if valid and all(matches) else None
        with store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            consumed = connection.execute(
                "UPDATE recovery_challenges SET attempts=attempts+1 WHERE token_hash=? AND attempts < 5 AND expires_at > ? AND session_hash=?",
                (token_hash, int(time.time()), sessions.token_hash(request)),
            ).rowcount
            success = False
            if consumed and new_hash:
                success = bool(
                    connection.execute(
                        "UPDATE users SET password_hash=? WHERE id=? AND password_hash=? AND security_json=?",
                        (new_hash, row[0], row[1], row[2]),
                    ).rowcount
                )
                if success:
                    connection.execute(
                        "DELETE FROM recovery_challenges WHERE user_id=?", (row[0],)
                    )
                    connection.execute(
                        "DELETE FROM sessions WHERE owner_id=?", (row[0],)
                    )
        if not success:
            raise HTTPException(
                400, "重置未完成，请确认账号名、三个密保答案及问题有效期。"
            )
        return {"message": "密码已重置，请使用新密码登录。"}

    @router.post("/security-questions")
    def set_security(payload: SecurityUpdate, request: Request):
        user = sessions.account(request)
        guard(request, user["username"], "security")
        with store.connect() as connection:
            old_hash = connection.execute(
                "SELECT password_hash FROM users WHERE id=?", (user["id"],)
            ).fetchone()[0]
        if not PASSWORDS.verify(payload.current_password, old_hash):
            raise HTTPException(400, "当前密码有误。")
        encoded = encoded_questions(payload.questions)
        with store.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if (
                sessions.current(request) != user["id"]
                or not connection.execute(
                    "UPDATE users SET security_json=? WHERE id=? AND password_hash=?",
                    (encoded, user["id"], old_hash),
                ).rowcount
            ):
                raise HTTPException(409, "账号状态已变化，请重新登录。")
            connection.execute(
                "DELETE FROM recovery_challenges WHERE user_id=?", (user["id"],)
            )
        return state(user["id"], sessions.token_hash(request))

    @router.post("/password")
    def change_password(payload: PasswordInput, request: Request):
        user = sessions.account(request)
        guard(request, user["username"], "password")
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
                "DELETE FROM recovery_challenges WHERE user_id = ?", (user["id"],)
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
                    "playback_preferences",
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
