import os
from pathlib import Path
from uuid import UUID, uuid4


def get_storage_dir() -> Path:
    """Return the configurable directory for uploaded datasets."""
    return Path(os.environ.get("DATA_STORAGE_DIR", "data/datasets")).resolve()


def save_dataset(content: bytes) -> str:
    """Save original bytes under a generated ID."""
    storage_dir = get_storage_dir()
    storage_dir.mkdir(parents=True, exist_ok=True)

    dataset_id = str(uuid4())
    path = storage_dir / f"{dataset_id}.csv"

    # Exclusive creation prevents overwriting an existing file.
    with path.open("xb") as file:
        file.write(content)

    return dataset_id


def load_dataset(dataset_id: str) -> bytes:
    """Retrieve a dataset using a validated UUID."""
    safe_id = str(UUID(dataset_id))
    path = get_storage_dir() / f"{safe_id}.csv"

    return path.read_bytes()