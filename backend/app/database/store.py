import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from app.core.config import DB

LOCK = threading.RLock()
TABLES = {'events', 'projects', 'scans', 'investigations', 'settings', 'assets', 'skills', 'knowledge', 'remediations', 'discoveries', 'intelligence', 'ti_sync'}

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def connect():
    c = sqlite3.connect(DB, timeout=30)
    c.execute('PRAGMA journal_mode=WAL')
    try:
        with c:
            yield c
    finally:
        c.close()

def init():
    with LOCK, connect() as c:
        for table in TABLES:
            c.execute(f'CREATE TABLE IF NOT EXISTS {table} (id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated TEXT NOT NULL)')
    DB.chmod(0o600)

def put(table, obj):
    assert table in TABLES
    with LOCK, connect() as c:
        c.execute(f'INSERT INTO {table} VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, updated=excluded.updated', (obj['id'], json.dumps(obj, ensure_ascii=False), now()))
    return obj

def get(table, id):
    assert table in TABLES
    with connect() as c:
        row = c.execute(f'SELECT payload FROM {table} WHERE id=?', (id,)).fetchone()
    return json.loads(row[0]) if row else None

def all_rows(table):
    assert table in TABLES
    with connect() as c:
        rows = c.execute(f'SELECT payload FROM {table} ORDER BY updated DESC').fetchall()
    return [json.loads(row[0]) for row in rows]

def delete(table, id):
    assert table in TABLES
    with LOCK, connect() as c:
        c.execute(f"DELETE FROM {table} WHERE id=?", (id,))
