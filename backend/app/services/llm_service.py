"""AI 日程解析服务。

优先调用 OpenAI 兼容大模型（/chat/completions）把自然语言转成结构化日程；
未配置 LLM_API_KEY 或调用失败时自动降级为本地规则解析，保证无 Key 也能演示。
"""

import json
import re
from datetime import date, datetime, timedelta
from typing import Optional

import httpx

from ..config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT
from ..repositories import user_repo

WEEKDAYS_CN = {
    "一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6,
}
PERIOD_TIMES = {
    "凌晨": "05:00",
    "早晨": "07:00",
    "早上": "08:00",
    "上午": "09:00",
    "中午": "12:00",
    "傍晚": "18:00",
    "下午": "14:00",
    "晚上": "19:00",
}
_RANGE_RE = re.compile(
    r"(?<!\d)(\d{1,2})\s*[:：点]\s*(\d{1,2})?\s*分?\s*[-~—–至到]\s*"
    r"(\d{1,2})\s*[:：点]\s*(\d{1,2})?\s*分?(?!\d)"
)
_COLON_RE = re.compile(r"(?<!\d)(\d{1,2})\s*[:：]\s*([0-5]\d)(?!\d)")
_DIAN_RE = re.compile(r"(?<!\d)(\d{1,2})\s*点(?:(半)|(\d{1,2})\s*分)?(?!\d)")
_PREFIXES = [
    "请帮我", "麻烦帮我", "帮我安排一下", "帮我添加一个", "帮我新建一个",
    "帮我加一个", "帮我安排", "帮我添加", "帮我新建", "帮我记一下",
    "请安排", "请添加", "请新建", "安排一下", "添加一个", "新建一个",
    "添加", "新建", "安排", "记得", "预约", "预订",
]


# ---------------- 通用小工具 ----------------


def _hhmm(hour: int, minute: int = 0) -> str:
    hour = max(0, min(23, int(hour)))
    minute = max(0, min(59, int(minute)))
    return "{0:02d}:{1:02d}".format(hour, minute)


def _add_minutes(time_str: str, delta: int = 60) -> str:
    hour, minute = time_str.split(":")
    total = int(hour) * 60 + int(minute) + delta
    return "{0:02d}:{1:02d}".format((total // 60) % 24, total % 60)


def _is_valid_time(value: Optional[str]) -> bool:
    if not value:
        return False
    match = re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", value)
    return bool(match)


def _is_valid_date(value: Optional[str]) -> bool:
    if not value:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def _fix_time_pair(start: Optional[str], end: Optional[str]):
    """补齐缺失或非法的结束时间，保证 end > start。"""
    if not _is_valid_time(start):
        return None, None
    if not _is_valid_time(end) or end <= start:
        end = _add_minutes(start, 60)
    return start, end


# ---------------- 日期解析（本地规则） ----------------


def _parse_date_cn(text: str):
    """尝试从文本解析日期，返回 (YYYY-MM-DD, 命中片段)，找不到返回 None。"""
    today = date.today()
    for keyword, delta in (
        ("大前天", -3), ("前天", -2), ("昨天", -1),
        ("大后天", 3), ("后天", 2), ("明天", 1), ("明日", 1),
        ("今日", 0), ("今天", 0),
    ):
        if keyword in text:
            return (today + timedelta(days=delta)).isoformat(), keyword

    match = re.search(
        r"(20\d{2})\s*[年./-]\s*(\d{1,2})\s*[月./-]\s*(\d{1,2})\s*[日号]?", text
    )
    if match:
        year, month, day = (int(match.group(i)) for i in (1, 2, 3))
        return date(year, month, day).isoformat(), match.group(0)

    match = re.search(r"(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]", text)
    if match:
        month, day = int(match.group(1)), int(match.group(2))
        year = today.year if (month, day) >= (today.month, today.day) else today.year + 1
        try:
            return date(year, month, day).isoformat(), match.group(0)
        except ValueError:
            return None

    match = re.search(r"下\s*(?:个)?\s*[周星期]\s*([一二三四五六日天])", text)
    if match:
        target = WEEKDAYS_CN[match.group(1)]
        delta = (target - today.weekday()) % 7 or 7
        return (today + timedelta(days=delta)).isoformat(), match.group(0)

    match = re.search(r"(?:这|本)?\s*[周星期]\s*([一二三四五六日天])", text)
    if match:
        target = WEEKDAYS_CN[match.group(1)]
        delta = (target - today.weekday()) % 7
        return (today + timedelta(days=delta)).isoformat(), match.group(0)

    return None


# ---------------- 时间解析（本地规则） ----------------


def _parse_time_cn(text: str):
    """解析时间段，返回 (start, end, 命中的文本片段)，支持 14:00-15:00 / 下午3点等。"""
    period = ""
    default_start = None
    for keyword, start_value in PERIOD_TIMES.items():
        if keyword in text:
            period = keyword
            default_start = start_value
            break
    pm_hint = period in ("下午", "晚上", "傍晚", "中午")

    match = _RANGE_RE.search(text)
    if match:
        minute1 = int(match.group(2)) if match.group(2) else 0
        minute2 = int(match.group(4)) if match.group(4) else 0
        start = _resolve_hour(int(match.group(1)), minute1, pm_hint, bool(period))
        end = _resolve_hour(int(match.group(3)), minute2, pm_hint, bool(period))
        start, end = _fix_time_pair(start, end)
        return start, end, match.group(0)

    # 12:30 这类 24 小时制写法不转换
    match = _COLON_RE.search(text)
    if match:
        start = _hhmm(int(match.group(1)), int(match.group(2)))
        start, end = _fix_time_pair(start, None)
        return start, end, match.group(0)

    # “下午3点 / 3点半 / 9点30分” 这类口语写法
    match = _DIAN_RE.search(text)
    if match:
        minute = 30 if match.group(2) else (int(match.group(3)) if match.group(3) else 0)
        start = _resolve_hour(int(match.group(1)), minute, pm_hint, bool(period))
        start, end = _fix_time_pair(start, None)
        return start, end, match.group(0)

    if default_start:
        start, end = _fix_time_pair(default_start, None)
        return start, end, period
    return None, None, ""


def _resolve_hour(hour: int, minute: int, pm_hint: bool, has_period: bool) -> str:
    """口语小时转 24 小时制：下午/晚上 +12；无时段词时 1-7 点按下午理解。"""
    if pm_hint and 0 < hour < 12:
        hour += 12
    elif not has_period and 1 <= hour <= 7:
        hour += 12
    return _hhmm(hour, minute)


def _clean_title(rest: str) -> str:
    rest = re.sub(r"[，,。.;；、!！?？~～:：]+", " ", rest)
    rest = re.sub(r"\s+", " ", rest).strip()
    if not rest.startswith("下午茶"):
        for keyword in PERIOD_TIMES:
            if rest.startswith(keyword):
                rest = rest[len(keyword):].strip()
                break
    for prefix in _PREFIXES:
        if rest.startswith(prefix):
            rest = rest[len(prefix):].strip()
            break
    rest = re.sub(r"\s+", " ", rest).strip()
    return rest or "新日程"


def _parse_locally(text: str, users: list[dict]) -> dict:
    date_result = _parse_date_cn(text)
    date_str = date_result[0] if date_result else None
    start_time, end_time, time_text = _parse_time_cn(text)

    user = None
    for item in users:
        if item["name"] in text:
            user = item
            break

    rest = text
    for fragment in (date_result[1] if date_result else "", time_text):
        if fragment:
            rest = rest.replace(fragment, " ")
    if user:
        rest = rest.replace(user["name"], " ")

    return {
        "user_id": user["id"] if user else None,
        "user_name": user["name"] if user else "",
        "title": _clean_title(rest),
        "date": date_str,
        "start_time": start_time,
        "end_time": end_time,
        "location": "",
        "note": "",
        "source": "local",
    }


# ---------------- 大模型解析 ----------------


def _chat(messages: list[dict]) -> str:
    response = httpx.post(
        LLM_BASE_URL + "/chat/completions",
        headers={
            "Authorization": "Bearer " + LLM_API_KEY,
            "Content-Type": "application/json",
        },
        json={"model": LLM_MODEL, "messages": messages, "temperature": 0.1},
        timeout=LLM_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _extract_json(reply: str) -> dict:
    cleaned = re.sub(r"`(?:json)?", "", reply).strip(" \n")
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("大模型未返回有效 JSON")
    return json.loads(cleaned[start:end + 1])


def _build_messages(text: str, users: list[dict]) -> list[dict]:
    names = "、".join(item["name"] for item in users)
    system = (
        "你是团队日程解析助手，把用户的一句话日程解析为 JSON。"
        "今天是 {today}。输出必须只包含一个 JSON 对象，不要输出解释文字，格式如下："
        '{{"user_name": "成员姓名(没提到填空串)", "title": "日程标题", '
        '"date": "YYYY-MM-DD", "start_time": "HH:MM", "end_time": "HH:MM", '
        '"location": "地点(可为空)", "note": "备注(可为空)"}}。'
        "规则：date 必须根据今天计算成具体日期；时间为 24 小时制；"
        "user_name 只能从候选名单选择：{names}；无法确定就填空字符串。"
    ).format(today=date.today().isoformat(), names=names)
    example = (
        '输入："明天下午3点到4点 王五 和后端对接口" 输出：'
        '{"user_name":"王五","title":"和后端对接口","date":"{0}","start_time":"15:00",'
        '"end_time":"16:00","location":"","note":""}'
    ).format((date.today() + timedelta(days=1)).isoformat())
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": example + "\n输入：" + text},
    ]


def _normalize(raw: dict, users: list[dict]) -> dict:
    user = None
    name = str(raw.get("user_name") or "").strip()
    for item in users:
        if item["name"] == name or (name and name in item["name"]):
            user = item
            break
    if user is None:
        for item in users:
            if name and item["name"] in name:
                user = item
                break

    date_value = str(raw.get("date") or "").strip()
    if not _is_valid_date(date_value):
        try:
            date_value = datetime.fromisoformat(date_value).date().isoformat()
        except (ValueError, TypeError):
            date_value = ""
    start_time, end_time = _fix_time_pair(
        str(raw.get("start_time") or "").strip() or None,
        str(raw.get("end_time") or "").strip() or None,
    )
    title = str(raw.get("title") or "").strip() or "新日程"
    return {
        "user_id": user["id"] if user else None,
        "user_name": user["name"] if user else (name or ""),
        "title": title,
        "date": date_value or None,
        "start_time": start_time,
        "end_time": end_time,
        "location": str(raw.get("location") or "").strip(),
        "note": str(raw.get("note") or "").strip(),
        "source": "llm",
    }


# ---------------- 对外入口 ----------------


def parse_schedule(text: str) -> dict:
    """把自然语言解析为结构化日程（含 user_id / title / date / 起止时间等）。"""
    users = user_repo.list_users()
    if LLM_API_KEY:
        try:
            reply = _chat(_build_messages(text, users))
            return _normalize(_extract_json(reply), users)
        except Exception:
            pass  # 网络/模型异常时降级本地规则，保证接口可用
    return _parse_locally(text, users)
