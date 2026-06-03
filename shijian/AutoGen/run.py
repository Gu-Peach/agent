"""Run the AutoGen software-development team demo."""

import argparse
import asyncio

from autogen_agentchat.ui import Console

try:
    from .process import create_software_development_team
    from .role import create_openai_model_client
except ImportError:
    from process import create_software_development_team
    from role import create_openai_model_client


DEFAULT_TASK = """我们需要开发一个比特币价格显示应用，具体要求如下：

核心功能：
- 实时显示比特币当前价格（USD）
- 显示 24 小时价格变化趋势（涨跌幅和涨跌额）
- 提供价格刷新功能

技术要求：
- 使用 Streamlit 框架创建 Web 应用
- 界面简洁美观，用户友好
- 添加适当的错误处理和加载状态

请团队协作完成这个任务，从需求分析到最终实现。"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the AutoGen agent demo.")
    parser.add_argument(
        "--task",
        default=DEFAULT_TASK,
        help="Task prompt passed to the agent team.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=12,
        help="Maximum number of group-chat turns.",
    )
    parser.add_argument(
        "--with-user-proxy",
        action="store_true",
        help="Add a human input agent to the round-robin team.",
    )
    return parser.parse_args()


async def run_software_development_team(
    task: str = DEFAULT_TASK,
    include_user_proxy: bool = False,
    max_turns: int = 12,
):
    model_client = create_openai_model_client()
    team_chat = create_software_development_team(
        model_client=model_client,
        include_user_proxy=include_user_proxy,
        max_turns=max_turns,
    )

    try:
        return await Console(team_chat.run_stream(task=task))
    finally:
        await model_client.close()


def main() -> None:
    args = parse_args()
    asyncio.run(
        run_software_development_team(
            task=args.task,
            include_user_proxy=args.with_user_proxy,
            max_turns=args.max_turns,
        )
    )


if __name__ == "__main__":
    main()
