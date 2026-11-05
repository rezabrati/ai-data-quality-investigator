from io import BytesIO
import csv
import pandas as pd


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

    return {
        "row_count": row_count,
        "column_count": int(df.shape[1]),
        "duplicate_row_count": duplicate_count,
        "duplicate_row_percent": duplicate_percent,
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
            }
            for name in df.columns
        ],
    }