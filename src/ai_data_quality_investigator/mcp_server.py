from uuid import UUID

from mcp.server import MCPServer
from starlette.concurrency import run_in_threadpool

from ai_data_quality_investigator.profiling import summarize_csv
from ai_data_quality_investigator.storage import (
    load_dataset,
    load_metadata,
)

mcp = MCPServer("Data Quality Investigator")


@mcp.tool()
async def profile_dataset(dataset_id: UUID) -> dict[str, object]:
    """Profile a previously uploaded dataset using its dataset ID.

    Returns column statistics, data quality findings, and target
    analysis when saved target settings are available.
    Does not modify the dataset.
    """
    try:
        content = await run_in_threadpool(
            load_dataset,
            str(dataset_id),
        )
    except FileNotFoundError as exc:
        raise ValueError("Dataset not found. Upload it first.") from exc

    metadata = await run_in_threadpool(
        load_metadata,
        str(dataset_id),
    )

    summary = await run_in_threadpool(
        summarize_csv,
        content,
        target_column=metadata["target_column"],
        task_type=metadata["task_type"],
    )

    return {
        "dataset_id": str(dataset_id),
        "summary": summary,
    }


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8001,
    )