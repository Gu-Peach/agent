"""Agent roles and model-client helpers for the AutoGen demo."""

import os
from pathlib import Path

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_core.models import ModelFamily
from autogen_ext.models.openai import OpenAIChatCompletionClient


ENV_PATH = Path(__file__).with_name(".env")


def load_local_env(env_path: Path = ENV_PATH) -> None:
    """Load simple KEY=VALUE entries from .env without requiring python-dotenv."""
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def create_openai_model_client() -> OpenAIChatCompletionClient:
    """Create an OpenAI-compatible model client from .env or shell variables."""
    load_local_env()

    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing LLM_API_KEY or OPENAI_API_KEY. Please set it in shijian/AutoGen/.env."
        )

    client_kwargs = {
        "model": os.getenv("LLM_MODEL_ID") or os.getenv("OPENAI_MODEL") or "gpt-4o-mini",
        "api_key": api_key,
    }

    base_url = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    if base_url:
        client_kwargs["base_url"] = base_url

    if _uses_custom_openai_compatible_endpoint(base_url):
        client_kwargs["model_info"] = create_model_info()

    return OpenAIChatCompletionClient(**client_kwargs)


def _uses_custom_openai_compatible_endpoint(base_url: str | None) -> bool:
    if not base_url:
        return False

    normalized_base_url = base_url.rstrip("/")
    return normalized_base_url != "https://api.openai.com/v1"


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def create_model_info() -> dict:
    """Describe non-OpenAI models for AutoGen's compatibility checks."""
    return {
        "vision": _env_bool("LLM_MODEL_SUPPORTS_VISION", False),
        "function_calling": _env_bool("LLM_MODEL_SUPPORTS_FUNCTION_CALLING", True),
        "json_output": _env_bool("LLM_MODEL_SUPPORTS_JSON_OUTPUT", True),
        "family": os.getenv("LLM_MODEL_FAMILY", ModelFamily.UNKNOWN),
        "structured_output": _env_bool("LLM_MODEL_SUPPORTS_STRUCTURED_OUTPUT", True),
        "multiple_system_messages": _env_bool("LLM_MODEL_SUPPORTS_MULTIPLE_SYSTEM_MESSAGES", True),
    }


def create_product_manager(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create the product manager agent."""
    system_message = """你是一位经验丰富的产品经理，负责软件产品的需求分析和项目规划。

收到开发任务后，请按以下结构输出：
1. 需求理解与边界
2. 功能模块拆分
3. 技术选型建议
4. 实现优先级
5. 验收标准

请简洁、明确地回应。分析完成后，请提醒工程师开始实现。"""

    return AssistantAgent(
        name="ProductManager",
        model_client=model_client,
        system_message=system_message,
        model_client_stream=True,
    )


def create_engineer(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create the software engineer agent."""
    system_message = """你是一位资深 Python 软件工程师，擅长 Web 应用开发和第三方 API 集成。

收到任务后，请完成：
1. 技术方案说明
2. 可运行代码实现
3. 错误处理与边界情况
4. 运行方式说明

请输出完整、可执行的实现建议。完成后请说：请代码审查员检查。"""

    return AssistantAgent(
        name="Engineer",
        model_client=model_client,
        system_message=system_message,
        model_client_stream=True,
    )


def create_code_reviewer(model_client: OpenAIChatCompletionClient) -> AssistantAgent:
    """Create the code reviewer agent."""
    system_message = """你是一位代码审查专家，关注代码质量、安全性、可维护性和可运行性。

请审查工程师的实现，重点检查：
1. 代码结构是否清晰
2. 异常处理是否完整
3. API 调用是否安全可靠
4. 用户体验是否满足需求
5. 是否存在遗漏的测试或运行说明

如果实现可以接受，请给出简短结论，并在最后单独输出：TERMINATE"""

    return AssistantAgent(
        name="CodeReviewer",
        model_client=model_client,
        system_message=system_message,
        model_client_stream=True,
    )


def create_user_proxy() -> UserProxyAgent:
    """Create an optional human-in-the-loop user proxy."""
    return UserProxyAgent(name="UserProxy", input_func=input)


def create_default_agents(
    model_client: OpenAIChatCompletionClient,
    include_user_proxy: bool = False,
) -> list:
    """Create the default software-development team agents."""
    agents = [
        create_product_manager(model_client),
        create_engineer(model_client),
        create_code_reviewer(model_client),
    ]

    if include_user_proxy:
        agents.append(create_user_proxy())

    return agents
