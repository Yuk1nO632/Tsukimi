"""Transfer one administrator into an initialized empty database."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3

from dotenv import load_dotenv
from database import Database

FIELDS = ('id', 'email', 'nickname', 'password_hash', 'created_at', 'username', 'security_json', 'role')


def validate_record(record):
    if not isinstance(record, dict) or set(record) != set(FIELDS):
        raise ValueError('Unsupported administrator record.')
    if record['role'] != 'admin':
        raise ValueError('Only administrator records can be transferred.')
    if not all(isinstance(record[key], str) and record[key] for key in FIELDS if key != 'created_at'):
        raise ValueError('Invalid administrator fields.')
    if not re.fullmatch(r'[a-z0-9_]{4,32}', record['username']):
        raise ValueError('Invalid administrator username.')
    if type(record['created_at']) is not int or record['created_at'] < 0:
        raise ValueError('Invalid creation time.')
    if not record['password_hash'].startswith('$argon2'):
        raise ValueError('Unsupported password hash.')
    questions = json.loads(record['security_json'])
    if not isinstance(questions, list) or len(questions) not in (0, 3):
        raise ValueError('Invalid recovery questions.')
    for item in questions:
        if not isinstance(item, dict) or not isinstance(item.get('question'), str) or not isinstance(item.get('hash'), str) or not item['hash'].startswith('$argon2'):
            raise ValueError('Invalid recovery question record.')
    return record


def export_admin(database, username, output):
    database = Path(database).resolve()
    with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(f"SELECT {', '.join(FIELDS)} FROM users WHERE username = ?",
                                 (username.strip().lower(),)).fetchone()
    if row is None:
        raise ValueError('Administrator was not found.')
    record = validate_record(dict(row))
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({'version': 1, 'administrator': record}, ensure_ascii=False, indent=2)
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        stream.write(payload)
    return record['username']


def import_admin(database, source):
    database, source = Path(database).resolve(), Path(source)
    if not database.is_file():
        raise ValueError('Initialize the target database first.')
    if source.stat().st_size > 65536:
        raise ValueError('Transfer file is too large.')
    payload = json.loads(source.read_text(encoding='utf-8'))
    if not isinstance(payload, dict) or payload.get('version') != 1:
        raise ValueError('Unsupported transfer format.')
    record = validate_record(payload.get('administrator'))
    values = tuple(record[key] for key in FIELDS)
    with Database(database).connect() as connection:
        connection.execute('BEGIN IMMEDIATE')
        rows = connection.execute(f"SELECT {', '.join(FIELDS)} FROM users").fetchall()
        if rows:
            if rows == [values]:
                return record['username'], False
            raise ValueError('The target already contains another or modified account.')
        for table in ('owned_favorites', 'watch_progress', 'owned_source_bindings', 'playback_preferences'):
            if connection.execute(f'SELECT 1 FROM {table} LIMIT 1').fetchone():
                raise ValueError('Use a target database with empty business data.')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup = database.with_name(f'{database.stem}.pre-admin-import-{stamp}.db')
        with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as original:
            with closing(sqlite3.connect(backup)) as destination:
                original.backup(destination)
        connection.execute('INSERT INTO owners (id) VALUES (?)', (record['id'],))
        connection.execute(f"INSERT INTO users ({', '.join(FIELDS)}) VALUES ({', '.join('?' for _ in FIELDS)})", values)
    return record['username'], True


def main():
    backend = Path(__file__).resolve().parent
    load_dotenv(backend / '.env')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=Path(os.getenv('TSUKIMI_DATABASE', str(backend / 'data/tsukimi.db'))))
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export')
    export.add_argument('--username', required=True)
    export.add_argument('--output', required=True, type=Path)
    restore = commands.add_parser('import')
    restore.add_argument('--input', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'export':
            username = export_admin(args.database, args.username, args.output)
            print(f'Admin exported: {username}. File: {args.output}')
        else:
            username, changed = import_admin(args.database, args.input)
            print(f'Admin imported: {username}' if changed else f'Admin already imported: {username}')
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, f'Transfer stopped: {error}\n')


if __name__ == '__main__':
    main()
