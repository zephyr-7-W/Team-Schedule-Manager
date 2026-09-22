"""API 出入参模型（Pydantic）。"""

from typing import Optional

from pydantic import BaseModel, Field


class UserOut(BaseModel):
    id: int
    name: str
    role: str = ""
    color: str = ""


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=30)
    role: str = Field("", max_length=50)
    color: str = "#5470c6"


class ScheduleCreate(BaseModel):
    user_id: int
    title: str = Field(..., min_length=1, max_length=100)
    date: str
    start_time: str
    end_time: str
    location: str = ""
    note: str = ""
    category: str = "其他"
    recurrence: str = "none"
    participants: list[int] = []
    reminder: int = 10


class ScheduleUpdate(BaseModel):
    user_id: Optional[int] = None
    title: Optional[str] = None
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    note: Optional[str] = None
    category: Optional[str] = None
    recurrence: Optional[str] = None
    participants: Optional[list[int]] = None
    reminder: Optional[int] = None


class ScheduleShareRequest(BaseModel):
    """分享单条日程。channel: internal / feishu / dingtalk"""

    channel: str = "internal"
    message: str = ""


class MemberDayShareRequest(BaseModel):
    """分享某成员某一天的日程摘要。channel: internal / feishu / dingtalk"""

    date: str
    channel: str = "internal"
    message: str = ""


class AiParseRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)


class AiParseResponse(BaseModel):
    schedule: Optional[dict] = None
    conflicts: list[str] = []
    message: str = ""
    source: str = ""
