from typing import Callable, Any


class AgentTool:
    """Tool that can be used by agents to interact with the system.

    Tools with ``state_keys`` set can write values back into the LangGraph
    state.  When the callback returns a dict and ``state_keys`` is non-empty,
    the keys listed in ``state_keys`` are captured and can later be retrieved
    via ``consume_state_update()``, which ``Agent.run()`` merges into the
    returned state.
    """

    def __init__(
        self,
        name: str,
        description: str,
        callback: Callable[[dict[str, Any]], Any],
        state_keys: list[str] | None = None,
        parameters_schema: dict | None = None,
    ) -> None:
        """Initialize an agent tool.

        Args:
            name: Tool name/identifier.
            description: Tool description for the LLM.
            callback: Function to execute the tool.
            state_keys: Optional list of dict keys whose values should be
                merged back into the LangGraph state after execution.
            parameters_schema: JSON Schema dict describing the tool's parameters.
                When provided, this is forwarded to the LLM's native tool-calling
                API so the model knows exactly which fields to supply.
        """
        self.name = name
        self.description = description
        self.callback = callback
        self.state_keys: list[str] = state_keys or []
        self.parameters_schema: dict | None = parameters_schema
        self._pending_state: dict[str, Any] = {}

    def execute(self, params: dict[str, Any]) -> Any:
        """Execute the tool with the given parameters.

        Args:
            params: Parameters to pass to the tool callback.

        Returns:
            Result of the tool execution.
        """
        result = self.callback(params)
        if self.state_keys and isinstance(result, dict):
            self._pending_state = {k: result[k] for k in self.state_keys if k in result}
        else:
            self._pending_state = {}
        return result

    def consume_state_update(self) -> dict[str, Any]:
        """Return any pending state updates and clear the internal buffer.

        Called by ``Agent.run()`` after the tool-execution loop so that
        state-aware tools can propagate values into the LangGraph state.

        Returns:
            Dict of state keys → values (empty if the tool has no pending update).
        """
        update = self._pending_state
        self._pending_state = {}
        return update
