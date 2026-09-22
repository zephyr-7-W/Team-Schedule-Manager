"""第三方系统（飞书 / 钉钉）扩展壳。

当前仅返回占位响应，真实业务留待接入各开放平台后实现。
"""

from typing import Any


def _placeholder(channel: str, action: str, content: Any = None) -> dict:
    """生成统一的占位返回结构，方便前端识别扩展点。"""
    return {
        "channel": channel,
        "code": "PLACEHOLDER",
        "delivered": False,
        "action": action,
        "note": "[占位] 已预留接口，未接入真实 {0} 业务".format(channel),
        "content": content,
    }


def push_message(channel: str, content: str) -> dict:
    """向飞书 / 钉钉推送消息。

    扩展点：TODO 接入飞书机器人 / 钉钉机器人 webhook，鉴权 + 发送 + 重试。
    """
    return _placeholder(channel, "message_push", content)


def sync_organization(channel: str) -> dict:
    """从飞书 / 钉钉同步组织架构与成员。

    扩展点：TODO 调用通讯录接口拉取部门/成员，增量写入 users 表。
    """
    return _placeholder(channel, "org_sync", {"synced_members": 0})
