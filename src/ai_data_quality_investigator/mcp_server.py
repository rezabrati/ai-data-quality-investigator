from uuid import UUID

from mcp.server import MCPServer
from starlette.concurrency import run_in_threadpool
from ai_data_quality_investigator.investigation import category_frequencies
from ai_data_quality_investigator.profiling import summarize_csv
from ai_data_quality_investigator.storage import (
    load_dataset,
    load_metadata,
)
from ai_data_quality_investigator.investigation import (
    compare_target_by_category as calculate_target_by_category,
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

@mcp.tool()
async def get_category_frequencies(
    dataset_id: UUID,
    column: str,
    limit: int = 10,
) -> dict[str, object]:
    """Return the most frequent parsed values in a dataset column.

    Percentages use non-missing rows. Missing values are counted
    separately. Values are not normalized or modified.
    limit must be between 1 and 50.
    """
    try:
        content = await run_in_threadpool(
            load_dataset,
            str(dataset_id),
        )
    except FileNotFoundError as exc:
        raise ValueError("Dataset not found. Upload it first.") from exc

    frequencies = await run_in_threadpool(
        category_frequencies,
        content,
        column,
        limit,
    )

    return {
        "dataset_id": str(dataset_id),
        **frequencies,
    }

@mcp.tool()
async def compare_target_by_category(
    dataset_id: UUID,
    column: str,
    limit: int = 10,
) -> dict:
    """Compare classification target distributions within feature categories.

    Use this to investigate whether observed class proportions differ
    across categorical feature values. Results describe associations;
    they do not establish causation or confirm leakage.
    """
    try:
        content = await run_in_threadpool(
            load_dataset,
            str(dataset_id),
        )
        metadata = await run_in_threadpool(
            load_metadata,
            str(dataset_id),
        )
    except FileNotFoundError as exc:
        raise ValueError("Dataset not found.") from exc

    target_column = metadata.get("target_column")

    if (
        metadata.get("task_type") != "classification"
        or not target_column
    ):
        raise ValueError(
            "This tool requires a saved classification target."
        )

    comparison = await run_in_threadpool(
        calculate_target_by_category,
        content,
        column,
        target_column,
        limit,
    )

    return {
        "dataset_id": str(dataset_id),
        **comparison,
    }

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8001,
    )