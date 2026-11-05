from io import BytesIO
import csv
import pandas as pd

PLACEHOLDER_VALUES = {"unknown", "not provided", "not available"}

def summarize_csv(content: bytes) -> dict[str, object]:
    """Read a CSV and describe its structure."""
    try:
        # Inspect the beginning of the file to infer its delimiter.
        sample = content[:65_536].decode("utf-8-sig", errors="ignore")
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        except csv.Error as exc:
            raise ValueError(
                "Could not detect the separator. Use a consistent comma or semicolon delimiter."
            ) from exc
        df = pd.read_csv(
            BytesIO(content),
            sep=dialect.delimiter,
            encoding="utf-8-sig",
        )

    except UnicodeDecodeError as exc:
        raise ValueError("Please upload a UTF-8 encoded CSV.") from exc
    except pd.errors.EmptyDataError as exc:
        raise ValueError("The CSV has no columns to read.") from exc
    except pd.errors.ParserError as exc:
        raise ValueError("The CSV could not be parsed. Check its format.") from exc

    if df.empty:
        raise ValueError("The CSV contains headers but no data rows.")

    row_count = len(df)
    duplicate_count = int(df.duplicated().sum())
    duplicate_percent = round(duplicate_count / row_count * 100, 2)

    findings = []

    for name in df.columns:
        missing_count = int(df[name].isna().sum())

        if missing_count > 0:
            findings.append(
                {
                    "code": "missing_values",
                    "column": str(name),
                    "count": missing_count,
                    "message": (
                        f"Column '{name}' contains "
                        f"{missing_count} missing value(s)."
                    ),
                }
            )

        # Normalize text for comparison without modifying the dataset.
        text = df[name].astype("string")

        blank_count = int(
            text.str.fullmatch(r"\s*", na=False).sum()
        )

        placeholder_count = int(
            text.str.strip()
            .str.casefold()
            .isin(PLACEHOLDER_VALUES)
            .sum()
        )

        if blank_count > 0:
            findings.append(
                {
                    "code": "blank_values",
                    "column": str(name),
                    "count": blank_count,
                    "message": (
                        f"Column '{name}' contains "
                        f"{blank_count} whitespace-only value(s)."
                    ),
                }
            )

        if placeholder_count > 0:
            findings.append(
                {
                    "code": "placeholder_values",
                    "column": str(name),
                    "count": placeholder_count,
                    "message": (
                        f"Column '{name}' contains "
                        f"{placeholder_count} potential placeholder value(s)."
                    ),
                }
            )

    return {
        "row_count": row_count,
        "column_count": int(df.shape[1]),
        "duplicate_row_count": duplicate_count,
        "duplicate_row_percent": duplicate_percent,
        "findings": findings,
        "columns": [
            {
                "name": str(name),
                "dtype": str(df[name].dtype),
                "missing_count": int(df[name].isna().sum()),
                "missing_percent": round(
                    float(df[name].isna().mean()) * 100,
                    2,
                ),
                # Count non-null values containing only whitespace.
                "blank_count": int(
                    df[name]
                    .astype("string")
                    .str.fullmatch(r"\s*", na=False)
                    .sum()
                ),
                # Match placeholders regardless of case or surrounding spaces.
                "placeholder_count": int(
                    df[name]
                    .astype("string")
                    .str.strip()
                    .str.casefold()
                    .isin(PLACEHOLDER_VALUES)
                    .sum()
                ),
                # Count distinct values, excluding missing values.
                "unique_count": int(df[name].nunique(dropna=True)),
            }
            for name in df.columns
        ],
    }