from fastapi import FastAPI, HTTPException, UploadFile, Form
from starlette.concurrency import run_in_threadpool
from ai_data_quality_investigator.profiling import summarize_csv
from typing import Literal
from uuid import UUID
from ai_data_quality_investigator.storage import save_dataset, load_dataset, load_metadata

app = FastAPI(title="AI Data Quality Investigator")

MAX_FILE_SIZE = 10 * 1_000_000  # 10 MiB


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/datasets/upload")
async def upload_dataset(
    file: UploadFile,
    target_column: str | None = Form(default=None),
    task_type: Literal["classification", "regression"] | None = Form(default=None),) -> dict[str, object]:
    
    try:
        # Treat an empty target name as unspecified.
        target_column = (
            target_column.strip() or None
            if target_column is not None
            else None
        )

        # Require both inputs together, or neither.
        if (target_column is None) != (task_type is None):
            raise HTTPException(
                status_code=400,
                detail="Provide both target_column and task_type, or neither.",
            )
        # Check the extension; actual CSV parsing comes later.
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=400,
                detail="Please upload a .csv file.",
            )

        # Read at most the limit plus one byte to detect oversized files.
        content = await file.read(MAX_FILE_SIZE + 1)

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="File must be 10 MiB or smaller.",
            )

        if not content:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        try:
            summary = await run_in_threadpool(
                                                summarize_csv,
                                                content,
                                                target_column=target_column,
                                                task_type=task_type,
                                            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        dataset_id = await run_in_threadpool(save_dataset, content, target_column=target_column, task_type=task_type)

        return {
            "filename": file.filename,
            "size_mb": F"{round(len(content) / 1_000_000, 4)} MB",
            "target_column": target_column,
            "task_type": task_type,
            "summary": summary,
            "message": "CSV parsed successfully.",
            "dataset_id": dataset_id,
        }

    finally:
        await file.close()

@app.get("/datasets/{dataset_id}/profile")
async def profile_saved_dataset(
    dataset_id: UUID,
) -> dict[str, object]:
    # Load the CSV bytes before passing them to the profiler.
    try:
        content = await run_in_threadpool(
            load_dataset,
            str(dataset_id),
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Dataset not found.",
        ) from exc

    # Restore the target settings saved with the CSV.
    metadata = await run_in_threadpool(
        load_metadata,
        str(dataset_id),
    )

    try:
        summary = await run_in_threadpool(
            summarize_csv,
            content,
            target_column=metadata["target_column"],
            task_type=metadata["task_type"],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "dataset_id": str(dataset_id),
        "summary": summary,
    }