import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from fastapi.testclient import TestClient
from accounts import PASSWORDS
from create_admin import create_admin
from database import Database
from main import create_app
from transfer_admin import export_admin, import_admin


class AdminTransferTests(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.source = Database(Path(self.directory) / 'source.db')
        self.target = Database(Path(self.directory) / 'target.db')
        self.source.initialize()
        self.target.initialize()
        self.user = create_admin(self.source, 'Megumi', 'qa-transfer-password')
        self.output = Path(self.directory) / 'admin.json'

    def test_only_admin_credentials_and_questions_survive_and_login_works(self):
        questions = [{'question': f'Question {i}', 'hash': PASSWORDS.hash(f'answer-{i}')} for i in range(3)]
        with self.source.connect() as connection:
            connection.execute('UPDATE users SET security_json=?', (json.dumps(questions),))
            connection.execute('INSERT INTO owned_favorites VALUES (?,?,?,?,?)', (self.user['id'], 'bgm-400602', 1, 'watching', 1))
        create_admin(self.source, 'Other', 'other-qa-password')
        export_admin(self.source.path, 'Megumi', self.output)
        self.assertEqual(import_admin(self.target.path, self.output), ('megumi', True))
        self.assertEqual(self.target.user(self.user['id'])['role'], 'admin')
        self.assertEqual(self.target.list_collection(self.user['id']), [])
        self.assertEqual(self.target.list_progress(self.user['id']), [])
        backup = next(Path(self.directory).glob('target.pre-admin-import-*.db'))
        with closing(sqlite3.connect(backup)) as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM users').fetchone()[0], 0)
        with TestClient(create_app(database_path=self.target.path)) as client:
            client.get('/api/account')
            response = client.post('/api/account/login', json={'username': 'Megumi', 'password': 'qa-transfer-password'})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['user']['role'], 'admin')
            recovery = client.post('/api/account/recovery', json={'username': 'Megumi'}).json()
            self.assertEqual(recovery['questions'], [item['question'] for item in questions])

    def test_repeated_import_is_idempotent(self):
        export_admin(self.source.path, 'Megumi', self.output)
        import_admin(self.target.path, self.output)
        self.assertEqual(import_admin(self.target.path, self.output), ('megumi', False))
        self.assertEqual(len(list(Path(self.directory).glob('target.pre-admin-import-*.db'))), 1)

    def test_existing_target_account_and_existing_export_are_preserved(self):
        export_admin(self.source.path, 'Megumi', self.output)
        original = self.output.read_bytes()
        with self.assertRaises(FileExistsError):
            export_admin(self.source.path, 'Megumi', self.output)
        self.assertEqual(self.output.read_bytes(), original)
        other = create_admin(self.target, 'Other', 'other-qa-password')
        with self.assertRaises(ValueError):
            import_admin(self.target.path, self.output)
        self.assertIsNotNone(self.target.user(other['id']))
        self.assertIsNone(self.target.user(self.user['id']))

    def test_non_admin_and_invalid_transfer_are_rejected(self):
        with self.source.connect() as connection:
            connection.execute("UPDATE users SET role='user'")
        with self.assertRaises(ValueError):
            export_admin(self.source.path, 'Megumi', self.output)
        self.output.write_text(json.dumps({'version': 1, 'administrator': {'role': 'user'}}), encoding='utf-8')
        with self.assertRaises(ValueError):
            import_admin(self.target.path, self.output)
        with self.target.connect() as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM users').fetchone()[0], 0)

    def test_target_anonymous_business_data_is_preserved(self):
        export_admin(self.source.path, 'Megumi', self.output)
        with self.target.connect() as connection:
            connection.execute("INSERT INTO owners VALUES ('anonymous')")
            connection.execute("INSERT INTO owned_favorites VALUES ('anonymous','bgm-400602',1,'wish',1)")
        with self.assertRaises(ValueError):
            import_admin(self.target.path, self.output)
        with self.target.connect() as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM users').fetchone()[0], 0)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM owned_favorites').fetchone()[0], 1)
