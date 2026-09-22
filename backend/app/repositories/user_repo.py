"""用户表数据访问层（raw SQL，保持轻量）。"""

from typing import Optional

from ..database import db_cursor


def _to_dict(row) -> dict:
    return {"id": row["id"], "name": row["name"], "role": row["role"], "color": row["color"]}


def list_users() -> list[dict]:
    with db_cursor() as cur:
        rows = cur.execute(
            "SELECT id, name, role, color FROM users ORDER BY id"
        ).fetchall()
    return [_to_dict(r) for r in rows]


def get_user(user_id: int) -> Optional[dict]:
    with db_cursor() as cur:
        row = cur.execute(
            "SELECT id, name, role, color FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return _to_dict(row) if row else None


def create_user(name: str, role: str, color: str) -> dict:
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO users (name, role, color) VALUES (?, ?, ?)",
            (name.strip(), role.strip(), color),
        )
        user_id = cur.lastrowid
    result = get_user(user_id)
    assert result is not None
    return result


def delete_user(user_id: int) -> bool:
    """删除成员，同时清理其参与的共享日程组。"""
    with db_cursor(commit=True) as cur:
        shared_ids = [
            row["shared_id"]
            for row in cur.execute(
                "SELECT shared_id FROM schedules WHERE user_id = ? AND shared_id != ''",
                (user_id,),
            ).fetchall()
        ]
        for shared_id in shared_ids:
            cur.execute("DELETE FROM schedules WHERE shared_id = ?", (shared_id,))
        cur.execute("DELETE FROM schedules WHERE user_id = ?", (user_id,))
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return cur.rowcount > 0
