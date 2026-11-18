from typing import Any

from agents.mcp import MCPServerStreamableHttp


class LimitedMCPServer(MCPServerStreamableHttp):
    """Limit tool invocations for one investigation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._limits = {
            "profile_dataset": 1,
            "get_category_frequencies": 1,
            "compare_target_by_category": 1,
        }
        self._counts: dict[str, int] = {}

    async def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None,
        meta: dict[str, Any] | None = None,
    ):
        limit = self._limits.get(tool_name)

        if limit is None:
            raise ValueError(f"Tool '{tool_name}' is not permitted.")

        used = self._counts.get(tool_name, 0)

        if used >= limit:
            raise ValueError(
                f"Tool '{tool_name}' has reached its "
                f"limit of {limit} call per investigation."
            )

        # Reserve the call before awaiting execution.
        # Failed attempts also consume the allowance.
        self._counts[tool_name] = used + 1

        if meta is None:
            return await super().call_tool(tool_name, arguments)

        return await super().call_tool(
            tool_name,
            arguments,
            meta=meta,
        )