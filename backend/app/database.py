"""SQLite 连接与建表。

原型阶段使用 Python 内置 sqlite3 + 轻量仓储层；
后续需要复杂查询/迁移时，可平滑替换为 SQLAlchemy + Alembic。
"""

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from .config import DATA_DIR, DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL DEFAULT '',
    color TEXT NOT NULL DEFAULT '#5470c6',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    location TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '其他',
    recurrence TEXT NOT NULL DEFAULT 'none',
    participants TEXT NOT NULL DEFAULT '[]',
    reminder INTEGER NOT NULL DEFAULT 10,
    shared_id TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_schedules_date ON schedules(date);
CREATE INDEX IF NOT EXISTS idx_schedules_user_date ON schedules(user_id, date);
"""


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_cursor(commit: bool = False) -> Iterator[sqlite3.Cursor]:
    """统一数据库访问入口：with db_cursor(commit=True) as cur: cur.execute(...)"""
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """幂等初始化数据表。"""
    with db_cursor(commit=True) as cur:
        cur.executescript(_SCHEMA)
        columns = {row["name"] for row in cur.execute("PRAGMA table_info(schedules)").fetchall()}
        migrations = {
            "category": "ALTER TABLE schedules ADD COLUMN category TEXT NOT NULL DEFAULT '其他'",
            "recurrence": "ALTER TABLE schedules ADD COLUMN recurrence TEXT NOT NULL DEFAULT 'none'",
            "participants": "ALTER TABLE schedules ADD COLUMN participants TEXT NOT NULL DEFAULT '[]'",
            "reminder": "ALTER TABLE schedules ADD COLUMN reminder INTEGER NOT NULL DEFAULT 10",
            "shared_id": "ALTER TABLE schedules ADD COLUMN shared_id TEXT NOT NULL DEFAULT ''",
        }
        for name, statement in migrations.items():
            if name not in columns:
                cur.execute(statement)
