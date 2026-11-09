import asyncio
import json
import sys

from mcp import Client


async def main(dataset_id: str) -> None:
    async with Client("http://127.0.0.1:8001/mcp") as client:
        # Discover the tools exposed by the server.
        tools = await client.list_tools()
        print("Available tools:", [tool.name for tool in tools.tools])

        # Call our tool through MCP.
        result = await client.call_tool(
            "profile_dataset",
            {"dataset_id": dataset_id},
        )

        if result.is_error:
            print("Tool failed:", result.content)
            raise SystemExit(1)

        print(json.dumps(result.structured_content, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: uv run python -m "
            "ai_data_quality_investigator.mcp_client DATASET_ID"
        )

    asyncio.run(main(sys.argv[1]))