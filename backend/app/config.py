"""全局配置。

大模型统一走 OpenAI 兼容的 /chat/completions 协议，
通过环境变量注入；未配置 Key 时 AI 接口自动降级为本地规则解析。
"""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
DB_PATH = DATA_DIR / "schedule.db"

# ---- OpenAI 兼容大模型配置（DeepSeek / 通义 / 智谱 / vLLM 等均可）----
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "30"))
