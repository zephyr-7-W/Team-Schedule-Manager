"""日程业务服务层：字段校验、读写编排、冲突检测、分享文本组装。"""

import re
import uuid
from datetime import date, datetime
from typing import Optional

from ..repositories import schedule_repo, user_repo
from . import integration_service

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_UPDATABLE = (
    "user_id", "title", "date", "start_time", "end_time", "location", "note",
    "category", "recurrence", "participants", "reminder",
)


def today_str() -> str:
    return date.today().isoformat()


def _is_valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def _validate_fields(payload: dict) -> None:
    if "title" in payload and not str(payload["title"] or "").strip():
        raise ValueError("日程标题不能为空")
    if "date" in payload and not _is_valid_date(payload["date"]):
        raise ValueError("日期格式应为 YYYY-MM-DD")
    for key in ("start_time", "end_time"):
        if key in payload and not _TIME_RE.match(str(payload[key] or "")):
            raise ValueError("{0} 格式应为 HH:MM".format(key))
    if "user_id" in payload:
        if user_repo.get_user(payload["user_id"]) is None:
            raise ValueError("成员不存在")
    start = payload.get("start_time")
    end = payload.get("end_time")
    if start is not None and end is not None and start >= end:
        raise ValueError("结束时间必须晚于开始时间")


def list_schedules(date_str: Optional[str] = None, user_id: Optional[int] = None) -> list[dict]:
    """按日期查询全员日程（可按成员过滤）。"""
    target = date_str or today_str()
    _validate_fields({"date": target})
    if user_id is not None and user_repo.get_user(user_id) is None:
        raise ValueError("成员不存在")
    return schedule_repo.list_by_date(target, user_id)


def list_user_schedules(user_id: int, date_str: Optional[str] = None) -> list[dict]:
    """按成员查询其个人日程（可限定日期）。"""
    if user_repo.get_user(user_id) is None:
        raise ValueError("成员不存在")
    if date_str:
        _validate_fields({"date": date_str})
    return schedule_repo.list_by_user(user_id, date_str)


def create_schedule(payload: dict) -> dict:
    _validate_fields(payload)
    fields = {key: payload[key] for key in _UPDATABLE if key in payload}
    participant_ids = list(dict.fromkeys([payload["user_id"], *(payload.get("participants") or [])]))
    for participant_id in participant_ids:
        if user_repo.get_user(participant_id) is None:
            raise ValueError("参与人不存在")
    shared_id = uuid.uuid4().hex
    fields["shared_id"] = shared_id
    owner_id = payload["user_id"]
    for participant_id in participant_ids:
        row = dict(fields)
        row["user_id"] = participant_id
        schedule_repo.create(row)
    schedule = next(
        (item for item in schedule_repo.list_by_shared_id(shared_id) if item["user_id"] == owner_id),
        None,
    )
    assert schedule is not None
    return schedule


def update_schedule(schedule_id: int, payload: dict) -> dict:
    current = schedule_repo.get_by_id(schedule_id)
    if current is None:
        raise ValueError("日程不存在或已被删除")
    merged = dict(current)
    for key in _UPDATABLE:
        if payload.get(key) is not None:
            merged[key] = payload[key]
    _validate_fields({key: merged[key] for key in _UPDATABLE})
    changed = {key: payload[key] for key in _UPDATABLE if payload.get(key) is not None}
    if current.get("shared_id"):
        shared_changed = {key: value for key, value in changed.items() if key != "user_id"}
        if shared_changed:
            schedule_repo.update_shared(current["shared_id"], shared_changed)
        if "user_id" in changed:
            schedule_repo.update(schedule_id, {"user_id": changed["user_id"]})
    else:
        schedule_repo.update(schedule_id, changed)
    updated = schedule_repo.get_by_id(schedule_id)
    assert updated is not None
    return updated


def delete_schedule(schedule_id: int) -> None:
    current = schedule_repo.get_by_id(schedule_id)
    deleted = (
        schedule_repo.delete_shared(current["shared_id"])
        if current and current.get("shared_id")
        else schedule_repo.delete(schedule_id)
    )
    if not deleted:
        raise ValueError("日程不存在或已被删除")


def get_schedule(schedule_id: int) -> dict:
    schedule = schedule_repo.get_by_id(schedule_id)
    if schedule is None:
        raise ValueError("日程不存在或已被删除")
    return schedule


def detect_conflicts(
    date_str: str,
    user_id: Optional[int],
    start_time: str,
    end_time: str,
    exclude_id: Optional[int] = None,
) -> list[dict]:
    """简单冲突检测：返回同人同时段重叠的日程。"""
    if user_id is None:
        return []
    return schedule_repo.find_overlaps(
        date_str, user_id, start_time, end_time, exclude_id
    )


def conflict_messages(overlaps: list[dict]) -> list[str]:
    messages = []
    for item in overlaps:
        messages.append(
            "冲突：{0} {1}-{2} 已有日程「{3}」，与本次时间重叠".format(
                item["user"]["name"], item["start_time"], item["end_time"], item["title"]
            )
        )
    return messages


def _format_time(value: str) -> str:
    return value[:5]


def build_digest(member_name: str, date_str: str, schedules: list[dict], extra: str = "") -> str:
    lines = ["【{0}】{1} 的日程".format(date_str, member_name)]
    if not schedules:
        lines.append("（当天暂无日程）")
    for item in schedules:
        line = "{0}-{1}  {2}".format(
            _format_time(item["start_time"]), _format_time(item["end_time"]), item["title"]
        )
        if item.get("location"):
            line += "  @{0}".format(item["location"])
        lines.append(line)
    if extra:
        lines.append("附言：" + extra)
    return "\n".join(lines)


def _push_result(channel: str, content: str) -> dict:
    """按渠道分发：飞书/钉钉走占位壳，internal 直接返回。"""
    if channel in ("feishu", "dingtalk"):
        return integration_service.push_message(channel, content)
    return {
        "channel": "internal",
        "code": "OK",
        "delivered": True,
        "action": "internal_share",
        "note": "分享内容已生成，可直接复制转发",
        "content": content,
    }


def share_schedule(schedule_id: int, channel: str, extra: str = "") -> dict:
    """分享单条日程，返回内容与渠道推送占位结果。"""
    schedule = get_schedule(schedule_id)
    member = schedule["user"]
    content = build_digest(member["name"], schedule["date"], [schedule], extra)
    payload = _push_result(channel, content)
    return {"schedule": schedule, "content": content, "payload": payload}


def share_member_day(user_id: int, date_str: str, channel: str, extra: str = "") -> dict:
    """分享某成员某一天的日程摘要。"""
    member = user_repo.get_user(user_id)
    if member is None:
        raise ValueError("成员不存在")
    _validate_fields({"date": date_str})
    schedules = schedule_repo.list_by_user(user_id, date_str)
    content = build_digest(member["name"], date_str, schedules, extra)
    payload = _push_result(channel, content)
    return {"member": member, "schedules": schedules, "content": content, "payload": payload}
