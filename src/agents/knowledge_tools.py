"""Agent-scoped tools for browsing role knowledge documentation."""

from pydantic import BaseModel, ValidationError

from src.agents.knowledge import KnowledgeBase
from src.agents.llm.tool import AgentTool


class ListKnowledgeParams(BaseModel):
    """No parameters — lists all documents in this agent's knowledge base."""


class ReadKnowledgeParams(BaseModel):
    document_key: str


def _validate(model_cls: type[BaseModel], params: dict):
    try:
        return model_cls.model_validate(params), None
    except ValidationError as exc:
        messages = "; ".join(
            f"{' → '.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        )
        return None, f"Tool call validation error: {messages}"


def create_knowledge_tools(knowledge_base: KnowledgeBase) -> list[AgentTool]:
    """Build list_knowledge and read_knowledge tools scoped to one agent role."""

    def _list_callback(_params: dict) -> str:
        keys = sorted(knowledge_base.get_all_keys())
        if not keys:
            return "No knowledge documents available for this agent."
        lines = [
            "Documents available in your role knowledge base:",
            *(f"- {key}" for key in keys),
            "",
            "Call read_knowledge with document_key to load a document before producing work.",
        ]
        return "\n".join(lines)

    def _read_callback(params: dict) -> str:
        p, err = _validate(ReadKnowledgeParams, params)
        if err:
            return f"ERROR: {err}"
        assert p is not None
        key = p.document_key.strip().replace("\\", "/")
        content = knowledge_base.get_document(key)
        if content is None:
            known = ", ".join(sorted(knowledge_base.get_all_keys()))
            return (
                f"ERROR: Unknown document_key '{key}'. "
                f"Call list_knowledge first. Known keys: {known}"
            )
        return content

    return [
        AgentTool(
            name="list_knowledge",
            description=(
                "List markdown guides available to your role in knowledge/.\n"
                "Call this when you need to find documentation on how to do your work.\n"
                "Returns: document keys you can pass to read_knowledge."
            ),
            callback=_list_callback,
            parameters_schema=ListKnowledgeParams.model_json_schema(),
        ),
        AgentTool(
            name="read_knowledge",
            description=(
                "Load a role knowledge document by key from list_knowledge.\n"
                "Use for deeper guidance beyond the injected quality rubric.\n"
                "Args:\n"
                "  document_key: Key from list_knowledge (e.g. 'vision_document_guide.md').\n"
                "Returns: full markdown document text."
            ),
            callback=_read_callback,
            parameters_schema=ReadKnowledgeParams.model_json_schema(),
        ),
    ]
