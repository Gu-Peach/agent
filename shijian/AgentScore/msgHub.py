"""AgentScope 2.0 Werewolf demo built around a MsgHub-style message room."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, SecretStr, create_model

try:
    from agentscope.agent import Agent
    from agentscope.credential import DashScopeCredential
    from agentscope.formatter import DashScopeMultiAgentFormatter
    from agentscope.message import AssistantMsg, Msg, SystemMsg, UserMsg
    from agentscope.model import DashScopeChatModel
except ImportError as exc:
    raise ImportError(
        "AgentScope is required. Install it with: "
        "pip install -r shijian/AgentScore/requirements.txt"
    ) from exc


MAX_DISCUSSION_ROUND = 2
DEFAULT_ENV_PATH = Path(__file__).with_name(".env")


class DiscussionModelCN(BaseModel):
    """讨论阶段的输出格式。"""

    reach_agreement: bool = Field(description="是否已达成一致意见", default=False)
    confidence_level: int = Field(
        description="对当前推理的信心程度(1-10)",
        ge=1,
        le=10,
        default=5,
    )
    key_evidence: Optional[str] = Field(
        description="支持你观点的关键证据",
        default=None,
    )


class WerewolfKillModelCN(BaseModel):
    """狼人击杀投票的输出格式。"""

    target_name: str = Field(description="今晚想击杀的玩家姓名")
    reason: str = Field(description="选择该目标的理由")


class WitchActionModelCN(BaseModel):
    """女巫行动的输出格式。"""

    use_antidote: bool = Field(description="是否使用解药")
    use_poison: bool = Field(description="是否使用毒药")
    target_name: Optional[str] = Field(description="毒药目标玩家姓名", default=None)


@dataclass(frozen=True)
class PlayerConfig:
    """Player identity used to create an AgentScope agent."""

    name: str
    role: str
    character: str


class Moderator:
    """Creates moderator messages for the game."""

    async def announce(self, content: str) -> Msg:
        return UserMsg("Moderator", content)


class MsgHub:
    """A small local message room compatible with this demo.

    AgentScope 2.0 no longer exposes the old pipeline MsgHub API. This class
    keeps the same idea: observe an announcement, optionally broadcast each
    speaker's reply to the other agents, and cleanly scope that behavior.
    """

    def __init__(
        self,
        participants: list[Agent],
        enable_auto_broadcast: bool = True,
        announcement: Msg | None = None,
    ) -> None:
        self.participants = participants
        self.enable_auto_broadcast = enable_auto_broadcast
        self.announcement = announcement

    async def __aenter__(self) -> "MsgHub":
        if self.announcement is not None:
            await self.broadcast(self.announcement)
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    def set_auto_broadcast(self, enabled: bool) -> None:
        self.enable_auto_broadcast = enabled

    async def broadcast(self, msg: Msg, exclude: Agent | None = None) -> None:
        for agent in self.participants:
            if agent is not exclude:
                await agent.observe(msg)

    async def ask(
        self,
        agent: Agent,
        msg: Msg | None = None,
        structured_model: type[BaseModel] | dict | None = None,
    ) -> Msg:
        reply_msg = await agent_reply(
            agent,
            msg=msg,
            structured_model=structured_model,
        )
        if self.enable_auto_broadcast:
            await self.broadcast(reply_msg, exclude=agent)
        return reply_msg


def load_local_env(env_path: Path = DEFAULT_ENV_PATH) -> None:
    """Load simple KEY=VALUE entries from .env without requiring python-dotenv."""
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def create_dashscope_model() -> DashScopeChatModel:
    """Create the DashScope model used by all game agents."""
    load_local_env()

    api_key = os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing LLM_API_KEY or DASHSCOPE_API_KEY in environment.")

    credential = DashScopeCredential(
        api_key=SecretStr(api_key),
        base_url=os.getenv(
            "LLM_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
    )
    return DashScopeChatModel(
        credential=credential,
        model=os.getenv("LLM_MODEL_ID", "qwen-max"),
        formatter=DashScopeMultiAgentFormatter(),
        stream=True,
    )


def create_player_agent(player: PlayerConfig, model: DashScopeChatModel) -> Agent:
    """Create one game player as an AgentScope Agent."""
    return Agent(
        name=player.name,
        system_prompt=get_role_prompt(player.role, player.character),
        model=model,
    )


def create_default_players() -> list[PlayerConfig]:
    """Create a small playable setup for the demo."""
    return [
        PlayerConfig("曹操", "狼人", "多疑而强势的枭雄"),
        PlayerConfig("司马懿", "狼人", "冷静隐忍的谋士"),
        PlayerConfig("刘备", "平民", "仁厚稳重的君主"),
        PlayerConfig("诸葛亮", "预言家", "谨慎睿智的军师"),
        PlayerConfig("孙尚香", "女巫", "果断敏锐的女将"),
        PlayerConfig("赵云", "平民", "忠诚勇敢的武将"),
    ]


def format_player_list(players: list[Any]) -> str:
    """Format players or agents for prompts."""
    return "、".join(get_player_name(player) for player in players)


def get_player_name(player: Any) -> str:
    return getattr(player, "name", str(player))


def get_role_prompt(role: str, character: str) -> str:
    """获取角色提示词，融合游戏规则与人物性格。"""
    base_prompt = f"""你是{character}，在这场三国狼人杀游戏中扮演{role}。

重要规则：
1. 你只能通过对话和推理参与游戏
2. 不要尝试调用任何外部工具或函数
3. 严格按照要求的 JSON 格式回复

角色特点：
"""

    if role == "狼人":
        return base_prompt + f"""
- 你是狼人阵营，目标是消灭所有好人
- 夜晚可以与其他狼人协商击杀目标
- 白天要隐藏身份，误导好人
- 以{character}的性格说话和行动
"""

    if role == "预言家":
        return base_prompt + f"""
- 你是好人阵营，目标是找出狼人
- 每晚可以查验一名玩家身份
- 白天要用逻辑引导大家投票
- 以{character}的性格说话和行动
"""

    if role == "女巫":
        return base_prompt + f"""
- 你是好人阵营，拥有解药和毒药
- 解药可以救下夜晚被狼人击杀的玩家
- 毒药可以毒杀一名你怀疑的玩家
- 以{character}的性格说话和行动
"""

    return base_prompt + f"""
- 你是好人阵营，目标是找出狼人
- 你没有特殊技能，需要依靠发言和投票判断局势
- 以{character}的性格说话和行动
"""


def get_vote_model_cn(alive_players: list[Any]) -> type[BaseModel]:
    """Create a structured vote model for the current alive players."""
    valid_names = format_player_list(alive_players)
    return create_model(
        "VoteModelCN",
        target_name=(str, Field(description=f"投票目标玩家姓名，只能从这些玩家中选择：{valid_names}")),
        reason=(str, Field(description="投票理由")),
    )


async def agent_reply(
    agent: Agent,
    msg: Msg | None = None,
    structured_model: type[BaseModel] | dict | None = None,
) -> Msg:
    """Reply with optional structured output for AgentScope 2.0."""
    if structured_model is None:
        return await agent.reply(msg)

    if msg is not None:
        await agent.observe(msg)

    messages = [
        SystemMsg("system", await agent._get_system_prompt()),
        *agent.state.context,
    ]
    response = await agent.model.generate_structured_output(
        messages=messages,
        structured_model=structured_model,
    )
    reply_msg = AssistantMsg(
        agent.name,
        str(response.content),
        metadata={"structured": response.content},
        usage=response.usage,
    )
    await agent.observe(reply_msg)
    return reply_msg


async def fanout_pipeline(
    agents: list[Agent],
    msg: Msg,
    structured_model: type[BaseModel] | dict | None = None,
    enable_gather: bool = False,
) -> list[Msg]:
    """Send the same message to agents and collect replies."""
    if enable_gather:
        return await asyncio.gather(
            *[
                agent_reply(
                    agent,
                    msg=msg,
                    structured_model=structured_model,
                )
                for agent in agents
            ],
        )

    replies: list[Msg] = []
    for agent in agents:
        replies.append(
            await agent_reply(
                agent,
                msg=msg,
                structured_model=structured_model,
            ),
        )
    return replies


def extract_target_name(msg: Any) -> Optional[str]:
    """Best-effort extraction of target_name from a structured reply."""
    content = getattr(msg, "metadata", {}).get("structured", getattr(msg, "content", msg))
    if isinstance(content, BaseModel):
        return getattr(content, "target_name", None)
    if isinstance(content, dict):
        return content.get("target_name")
    return getattr(content, "target_name", None)


def majority_target(vote_msgs: list[Any]) -> Optional[str]:
    """Pick the most-voted target from structured vote messages."""
    counts: dict[str, int] = {}
    for msg in vote_msgs:
        target_name = extract_target_name(msg)
        if target_name:
            counts[target_name] = counts.get(target_name, 0) + 1

    if not counts:
        return None

    return max(counts.items(), key=lambda item: item[1])[0]


class WerewolfGame:
    """Minimal Werewolf game flow integrated with AgentScope."""

    def __init__(
        self,
        players: list[PlayerConfig] | None = None,
        model: DashScopeChatModel | None = None,
    ) -> None:
        self.player_configs = players or create_default_players()
        self.model = model or create_dashscope_model()
        self.moderator = Moderator()

        self.players = [
            create_player_agent(player, self.model)
            for player in self.player_configs
        ]
        self.alive_players = list(self.players)
        self.werewolves = [
            agent
            for agent, player in zip(self.players, self.player_configs)
            if player.role == "狼人"
        ]

    async def werewolf_phase(self, round_num: int) -> Optional[str]:
        """狼人阶段，展示消息驱动的协作模式。"""
        if not self.werewolves:
            return None

        async with MsgHub(
            self.werewolves,
            enable_auto_broadcast=True,
            announcement=await self.moderator.announce(
                f"第{round_num}晚。狼人们，请讨论今晚的击杀目标。"
                f"存活玩家：{format_player_list(self.alive_players)}"
            ),
        ) as werewolves_hub:
            for _ in range(MAX_DISCUSSION_ROUND):
                for wolf in self.werewolves:
                    await werewolves_hub.ask(
                        wolf,
                        structured_model=DiscussionModelCN,
                    )

            werewolves_hub.set_auto_broadcast(False)
            kill_votes = await fanout_pipeline(
                self.werewolves,
                msg=await self.moderator.announce("请选择击杀目标"),
                structured_model=WerewolfKillModelCN,
                enable_gather=False,
            )

        return majority_target(kill_votes)

    async def day_vote_phase(self) -> Optional[str]:
        """白天投票阶段，收集并统计所有存活玩家的放逐投票。"""
        vote_msgs = await fanout_pipeline(
            self.alive_players,
            msg=await self.moderator.announce("请投票选择要淘汰的玩家"),
            structured_model=get_vote_model_cn(self.alive_players),
            enable_gather=False,
        )
        return majority_target(vote_msgs)

    async def run_demo(self) -> None:
        """Run one night phase and one day vote phase."""
        killed = await self.werewolf_phase(round_num=1)
        print(f"狼人击杀目标：{killed or '未能达成有效目标'}")

        banished = await self.day_vote_phase()
        print(f"白天投票目标：{banished or '未能达成有效目标'}")


async def main() -> None:
    game = WerewolfGame()
    await game.run_demo()


if __name__ == "__main__":
    asyncio.run(main())
