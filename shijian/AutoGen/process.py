"""Team orchestration for the AutoGen demo."""

from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat

try:
    from .role import create_default_agents
except ImportError:
    from role import create_default_agents


def create_software_development_team(
    model_client,
    include_user_proxy: bool = False,
    max_turns: int = 12,
) -> RoundRobinGroupChat:
    """Create a round-robin team for a small software-development workflow."""
    participants = create_default_agents(
        model_client=model_client,
        include_user_proxy=include_user_proxy,
    )

    return RoundRobinGroupChat(
        participants=participants,
        termination_condition=TextMentionTermination("TERMINATE"),
        max_turns=max_turns,
    )
