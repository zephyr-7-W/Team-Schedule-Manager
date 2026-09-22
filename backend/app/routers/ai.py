"""AI 接口：自然语言解析 + 冲突检测文字提示。"""

from fastapi import APIRouter

from ..schemas import AiParseRequest, AiParseResponse
from ..services import llm_service, schedule_service

router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.post("/parse", response_model=AiParseResponse)
def ai_parse_schedule(payload: AiParseRequest):
    """接收自然语言，解析出结构化日程，并给出简单冲突提示。"""
    candidate = llm_service.parse_schedule(payload.text)

    conflicts: list[str] = []
    if (
        candidate.get("user_id")
        and candidate.get("date")
        and candidate.get("start_time")
        and candidate.get("end_time")
    ):
        overlaps = schedule_service.detect_conflicts(
            candidate["date"],
            candidate["user_id"],
            candidate["start_time"],
            candidate["end_time"],
        )
        conflicts = schedule_service.conflict_messages(overlaps)

    messages = []
    if candidate.get("source") == "llm":
        messages.append("AI 解析完成，请核对后保存")
    else:
        messages.append("未配置 LLM_API_KEY，已使用本地规则解析")
    if not candidate.get("user_id"):
        messages.append("未能识别成员，请手动选择")
    if not candidate.get("date"):
        messages.append("未识别日期，默认按当前所选日期处理")
    if not candidate.get("start_time"):
        messages.append("未识别时间段，请手动填写起止时间")

    return AiParseResponse(
        schedule=candidate,
        conflicts=conflicts,
        message="；".join(messages),
        source=candidate.get("source", ""),
    )
