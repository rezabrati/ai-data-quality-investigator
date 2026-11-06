import os
from pathlib import Path
from uuid import UUID, uuid4
import json


def get_storage_dir() -> Path:
    """Return the configurable directory for uploaded datasets."""
    return Path(os.environ.get("DATA_STORAGE_DIR", "data/datasets")).resolve()


def save_dataset(content: bytes, *, target_column: str | None = None, task_type: str | None = None) -> str:
    """Save original bytes and their analysis settings."""
    storage_dir = get_storage_dir()
    storage_dir.mkdir(parents=True, exist_ok=True)

    dataset_id = str(uuid4())
    csv_path = storage_dir / f"{dataset_id}.csv"
    metadata_path = storage_dir / f"{dataset_id}.json"

    metadata = {
        "target_column": target_column,
        "task_type": task_type,
    }

    with csv_path.open("xb") as file:
        file.write(content)

    try:
        with metadata_path.open("x", encoding="utf-8") as file:
            json.dump(metadata, file)
    except Exception:
        # Remove the CSV if its metadata could not be saved.
        csv_path.unlink(missing_ok=True)
        raise

    return dataset_id


def load_dataset(dataset_id: str) -> bytes:
    """Retrieve a dataset using a validated UUID."""
    safe_id = str(UUID(dataset_id))
    path = get_storage_dir() / f"{safe_id}.csv"

    return path.read_bytes()

import os
from pathlib import Path
from uuid import UUID, uuid4
import json


def get_storage_dir() -> Path:
    """Return the configurable directory for uploaded datasets."""
    return Path(os.environ.get("DATA_STORAGE_DIR", "data/datasets")).resolve()


def save_dataset(content: bytes, *, target_column: str | None = None, task_type: str | None = None) -> str:
    """Save original bytes and their analysis settings."""
    storage_dir = get_storage_dir()
    storage_dir.mkdir(parents=True, exist_ok=True)

    dataset_id = str(uuid4())
    csv_path = storage_dir / f"{dataset_id}.csv"
    metadata_path = storage_dir / f"{dataset_id}.json"

    metadata = {
        "target_column": target_column,
        "task_type": task_type,
    }

    with csv_path.open("xb") as file:
        file.write(content)

    try:
        with metadata_path.open("x", encoding="utf-8") as file:
            json.dump(metadata, file)
    except Exception:
        # Remove the CSV if its metadata could not be saved.
        csv_path.unlink(missing_ok=True)
        raise

    return dataset_id

def load_metadata(dataset_id: str) -> dict[str, str | None]:
    """Load settings; older datasets have no saved settings."""
    safe_id = str(UUID(dataset_id))
    path = get_storage_dir() / f"{safe_id}.json"

    try:
        with path.open(encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return {
            "target_column": None,
            "task_type": None,
        }