"""日程表数据访问层（raw SQL，返回带 user 信息的完整行）。"""

import json
from typing import Optional

from ..database import db_cursor

_SELECT = """
SELECT s.id, s.user_id, s.title, s.date, s.start_time, s.end_time,
       s.location, s.note, s.source, s.category, s.recurrence,
       s.participants, s.reminder, s.shared_id,
       u.name AS user_name, u.role AS user_role, u.color AS user_color
FROM schedules s
JOIN users u ON u.id = s.user_id
"""

_COLUMNS = (
    "user_id", "title", "date", "start_time", "end_time", "location", "note",
    "category", "recurrence", "participants", "reminder", "shared_id",
)


def _serialize(row) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "title": row["title"],
        "date": row["date"],
        "start_time": row["start_time"],
        "end_time": row["end_time"],
        "location": row["location"] or "",
        "note": row["note"] or "",
        "source": row["source"],
        "category": row["category"] or "其他",
        "recurrence": row["recurrence"] or "none",
        "participants": json.loads(row["participants"] or "[]"),
        "reminder": row["reminder"] if row["reminder"] is not None else 10,
        "shared_id": row["shared_id"] or "",
        "user": {
            "id": row["user_id"],
            "name": row["user_name"],
            "role": row["user_role"],
            "color": row["user_color"],
        },
    }


def list_by_date(date_str: str, user_id: Optional[int] = None) -> list[dict]:
    sql = _SELECT + " WHERE s.date = ?"
    args: list = [date_str]
    if user_id is not None:
        sql += " AND s.user_id = ?"
        args.append(user_id)
    sql += " ORDER BY s.start_time, s.id"
    with db_cursor() as cur:
        rows = cur.execute(sql, args).fetchall()
    return [_serialize(r) for r in rows]


def list_by_user(user_id: int, date_str: Optional[str] = None) -> list[dict]:
    sql = _SELECT + " WHERE s.user_id = ?"
    args: list = [user_id]
    if date_str:
        sql += " AND s.date = ?"
        args.append(date_str)
    sql += " ORDER BY s.date, s.start_time"
    with db_cursor() as cur:
        rows = cur.execute(sql, args).fetchall()
    return [_serialize(r) for r in rows]


def get_by_id(schedule_id: int) -> Optional[dict]:
    with db_cursor() as cur:
        row = cur.execute(_SELECT + " WHERE s.id = ?", (schedule_id,)).fetchone()
    return _serialize(row) if row else None


def create(fields: dict) -> int:
    fields = dict(fields)
    if "participants" in fields:
        fields["participants"] = json.dumps(fields["participants"], ensure_ascii=False)
    columns = list(fields.keys())
    sql = (
        "INSERT INTO schedules ("
        + ", ".join(columns)
        + ", source) VALUES ("
        + ", ".join(["?"] * len(columns))
        + ", 'manual')"
    )
    with db_cursor(commit=True) as cur:
        cur.execute(sql, [fields[c] for c in columns])
        return cur.lastrowid


def update(schedule_id: int, fields: dict) -> bool:
    fields = dict(fields)
    if "participants" in fields:
        fields["participants"] = json.dumps(fields["participants"], ensure_ascii=False)
    sets = [c + " = ?" for c in fields]
    sql = (
        "UPDATE schedules SET "
        + ", ".join(sets)
        + ", updated_at = datetime('now','localtime') WHERE id = ?"
    )
    with db_cursor(commit=True) as cur:
        cur.execute(sql, [fields[c] for c in fields] + [schedule_id])
        return cur.rowcount > 0


def list_by_shared_id(shared_id: str) -> list[dict]:
    if not shared_id:
        return []
    with db_cursor() as cur:
        rows = cur.execute(_SELECT + " WHERE s.shared_id = ? ORDER BY s.id", (shared_id,)).fetchall()
    return [_serialize(r) for r in rows]


def update_shared(shared_id: str, fields: dict) -> bool:
    if not shared_id:
        return False
    fields = dict(fields)
    if "participants" in fields:
        fields["participants"] = json.dumps(fields["participants"], ensure_ascii=False)
    sets = [c + " = ?" for c in fields]
    sql = "UPDATE schedules SET " + ", ".join(sets) + ", updated_at = datetime('now','localtime') WHERE shared_id = ?"
    with db_cursor(commit=True) as cur:
        cur.execute(sql, [fields[c] for c in fields] + [shared_id])
        return cur.rowcount > 0


def delete_shared(shared_id: str) -> bool:
    if not shared_id:
        return False
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM schedules WHERE shared_id = ?", (shared_id,))
        return cur.rowcount > 0


def delete(schedule_id: int) -> bool:
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        return cur.rowcount > 0


def find_overlaps(
    date_str: str,
    user_id: int,
    start_time: str,
    end_time: str,
    exclude_id: Optional[int] = None,
) -> list[dict]:
    """冲突检测：同一成员、同一天、时间段相交的其他日程。"""
    sql = _SELECT + " WHERE s.date = ? AND s.user_id = ? AND s.start_time < ? AND s.end_time > ?"
    args: list = [date_str, user_id, end_time, start_time]
    if exclude_id is not None:
        sql += " AND s.id != ?"
        args.append(exclude_id)
    sql += " ORDER BY s.start_time"
    with db_cursor() as cur:
        rows = cur.execute(sql, args).fetchall()
    return [_serialize(r) for r in rows]
