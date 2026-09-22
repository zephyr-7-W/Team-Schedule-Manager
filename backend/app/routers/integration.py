"""第三方集成占位接口。

说明：飞书 / 钉钉 的消息推送与组织架构同步暂为「空壳」，
仅定义路径与返回结构，便于后续按各开放平台补齐真实实现。
"""

from fastapi import APIRouter, Body, HTTPException

from ..services import integration_service

router = APIRouter(prefix="/api/integration", tags=["第三方集成(占位)"])

_CHANNELS = ("feishu", "dingtalk")


def _check_channel(channel: str) -> None:
    if channel not in _CHANNELS:
        raise HTTPException(status_code=404, detail="仅支持 feishu / dingtalk")


@router.get("/{channel}/status")
def get_status(channel: str):
    """查询集成占位状态。"""
    _check_channel(channel)
    return {
        "channel": channel,
        "status": "placeholder",
        "note": "[占位] 待接入 {0} 开放平台".format(channel),
    }


@router.post("/{channel}/messages/push")
def push_message(
    channel: str,
    content: str = Body(default="", embed=True, description="待推送文本"),
):
    """占位：向 {channel} 推送一条消息。

    扩展点：TODO 接入飞书机器人 / 钉钉机器人，补充鉴权与重试。
    """
    _check_channel(channel)
    return integration_service.push_message(channel, content)


@router.post("/{channel}/org/sync")
def sync_organization(channel: str):
    """占位：从 {channel} 同步组织架构与成员。

    扩展点：TODO 拉取部门/成员后增量同步 users 表。
    """
    _check_channel(channel)
    return integration_service.sync_organization(channel)
