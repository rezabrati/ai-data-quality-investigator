from fastapi import FastAPI, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from ai_data_quality_investigator.profiling import summarize_csv

app = FastAPI(title="AI Data Quality Investigator")

MAX_FILE_SIZE = 10 * 1_000_000  # 10 MiB


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/datasets/upload")
async def upload_dataset(file: UploadFile) -> dict[str, object]:
    try:
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
            summary = await run_in_threadpool(summarize_csv, content)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return {
            "filename": file.filename,
            "size_mb": F"{round(len(content) / 1_000_000, 4)} MB",
            "summary": summary,
            "message": "CSV parsed successfully.",
        }

    finally:
        await file.close()