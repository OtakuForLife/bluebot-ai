from dataclasses import dataclass, field
from typing import List, Optional

from src.agents.llm.base_provider import LLMConfig
from src.agents.llm.tool import AgentTool
from src.events import EventHandler


@dataclass
class AgentConfig:
    """Configuration for an Agent instance."""
    event_handler: Optional[EventHandler] = None
    llm_config: Optional[LLMConfig] = None
    knowledge_path: str = ""
    tools: List[AgentTool] = field(default_factory=list)
    system_prompt: str = ""
    capabilities: List[str] = field(default_factory=list)
    """Task types this agent can handle (e.g. ["design", "art"]).

    Used by the task_dispatcher to find a capable agent for each open task.
    Leave empty for agents that do not participate in the task marketplace
    (e.g. the Project Director, which creates tasks rather than claiming them).
    """