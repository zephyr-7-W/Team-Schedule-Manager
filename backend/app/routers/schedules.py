"""日程相关接口：按日期查询全员日程、日程增删改、单条分享。"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..schemas import ScheduleCreate, ScheduleShareRequest, ScheduleUpdate
from ..services import schedule_service

router = APIRouter(prefix="/api/schedules", tags=["日程"])

_ALLOWED_CHANNELS = ("internal", "feishu", "dingtalk")


def _share_message(channel: str) -> str:
    if channel == "feishu":
        return "[占位] 已生成飞书推送内容，接入飞书开放平台后自动发送"
    if channel == "dingtalk":
        return "[占位] 已生成钉钉推送内容，接入钉钉机器人后自动发送"
    return "分享内容已生成，可复制转发给同事"


@router.get("")
def list_daily_schedules(
    date: Optional[str] = Query(None, description="YYYY-MM-DD，缺省为今天"),
    user_id: Optional[int] = Query(None, description="按成员过滤"),
):
    """按日期查询全员日程（可按成员过滤）。"""
    try:
        return schedule_service.list_schedules(date, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("", status_code=201)
def create_schedule(payload: ScheduleCreate):
    """新增日程。"""
    try:
        return schedule_service.create_schedule(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{schedule_id}")
def update_schedule(schedule_id: int, payload: ScheduleUpdate):
    """修改日程（只更新传入字段）。"""
    try:
        return schedule_service.update_schedule(
            schedule_id, payload.model_dump(exclude_unset=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int):
    """删除日程。"""
    try:
        schedule_service.delete_schedule(schedule_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/{schedule_id}/share")
def share_single_schedule(schedule_id: int, payload: ScheduleShareRequest):
    """分享单条日程（internal / feishu / dingtalk）。"""
    if payload.channel not in _ALLOWED_CHANNELS:
        raise HTTPException(status_code=400, detail="channel 仅支持 internal/feishu/dingtalk")
    try:
        result = schedule_service.share_schedule(
            schedule_id, payload.channel, payload.message
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "channel": payload.channel,
        "message": _share_message(payload.channel),
        "content": result["content"],
        "payload": result["payload"],
    }
