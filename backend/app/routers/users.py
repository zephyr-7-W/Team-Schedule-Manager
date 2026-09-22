"""成员相关接口：成员列表、个人日程查询、成员某日日程分享。"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..repositories import user_repo
from ..schemas import MemberDayShareRequest, UserCreate, UserOut
from ..services import schedule_service

router = APIRouter(prefix="/api/users", tags=["成员"])

_ALLOWED_CHANNELS = ("internal", "feishu", "dingtalk")


def _share_message(channel: str) -> str:
    if channel == "feishu":
        return "[占位] 已生成飞书推送内容，接入飞书开放平台后自动发送"
    if channel == "dingtalk":
        return "[占位] 已生成钉钉推送内容，接入钉钉机器人后自动发送"
    return "分享内容已生成，可复制转发给同事"


@router.get("", response_model=list[UserOut])
def list_members():
    """获取团队人员列表（原型使用本地种子数据）。"""
    return user_repo.list_users()


@router.post("", response_model=UserOut, status_code=201)
def create_member(payload: UserCreate):
    try:
        return user_repo.create_user(payload.name, payload.role, payload.color)
    except Exception as exc:
        if "UNIQUE" in str(exc).upper():
            raise HTTPException(status_code=400, detail="成员姓名已存在") from exc
        raise HTTPException(status_code=400, detail="新增成员失败") from exc


@router.delete("/{user_id}")
def delete_member(user_id: int):
    if user_repo.get_user(user_id) is None:
        raise HTTPException(status_code=404, detail="成员不存在")
    if not user_repo.delete_user(user_id):
        raise HTTPException(status_code=404, detail="成员不存在")
    return {"ok": True}


@router.get("/{user_id}", response_model=UserOut)
def get_member(user_id: int):
    member = user_repo.get_user(user_id)
    if member is None:
        raise HTTPException(status_code=404, detail="成员不存在")
    return member


@router.get("/{user_id}/schedules")
def get_member_schedules(
    user_id: int,
    date: Optional[str] = Query(None, description="YYYY-MM-DD，缺省返回全部"),
):
    """按人员 ID 查询个人日程（可按日期过滤）。"""
    try:
        return schedule_service.list_user_schedules(user_id, date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{user_id}/schedules/share")
def share_member_day(user_id: int, payload: MemberDayShareRequest):
    """分享某成员某一天的日程摘要（internal / feishu / dingtalk）。"""
    if payload.channel not in _ALLOWED_CHANNELS:
        raise HTTPException(status_code=400, detail="channel 仅支持 internal/feishu/dingtalk")
    try:
        result = schedule_service.share_member_day(
            user_id, payload.date, payload.channel, payload.message
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
