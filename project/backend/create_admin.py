"""Local administrator bootstrap. Passwords are entered interactively and stored as Argon2 hashes."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
import getpass
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from dotenv import load_dotenv
from accounts import LoginInput, PASSWORDS
from database import Database


def create_admin(store, username, password):
    credentials = LoginInput(username=username, password=password)
    if not re.fullmatch(r"[a-z0-9_]{4,32}", credentials.username):
        raise ValueError("账号名需要 4–32 位英文字母、数字或下划线。")
    with store.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT id, password_hash FROM users WHERE username=?",
            (credentials.username,),
        ).fetchone()
        if row:
            if not PASSWORDS.verify(credentials.password, row[1]):
                raise ValueError("该账号已存在且密码不同，未修改现有账号。")
            connection.execute("UPDATE users SET role='admin' WHERE id=?", (row[0],))
            return store.user(row[0]) | {"role": "admin"}
        owner = secrets.token_hex(16)
        connection.execute("INSERT INTO owners VALUES (?)", (owner,))
        connection.execute(
            """INSERT INTO users (id,email,nickname,password_hash,created_at,username,security_json,role)
            VALUES (?, ?, ?, ?, ?, ?, '[]', 'admin')""",
            (
                owner,
                f"unbound:{owner}",
                username.strip(),
                PASSWORDS.hash(credentials.password),
                int(time.time()),
                credentials.username,
            ),
        )
    return store.user(owner)


def main():
    backend = Path(__file__).resolve().parent
    load_dotenv(backend / ".env")
    parser = argparse.ArgumentParser(description="创建本机管理员账号")
    parser.add_argument("--username", required=True)
    args = parser.parse_args()
    password = getpass.getpass("Administrator password: ")
    store = Database(
        Path(os.getenv("TSUKIMI_DATABASE", str(backend / "data/tsukimi.db")))
    )
    if store.path.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = store.path.with_name(f"{store.path.stem}.pre-admin-{stamp}.db")
        with closing(sqlite3.connect(store.path)) as source, closing(
            sqlite3.connect(backup)
        ) as destination:
            source.backup(destination)
    store.initialize()
    user = create_admin(store, args.username, password)
    print(
        f"Administrator ready: {user['username']} ({user['role']}). Set recovery questions after login."
    )


if __name__ == "__main__":
    main()
