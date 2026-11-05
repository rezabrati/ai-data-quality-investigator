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

    columns = []
    findings = []

    if duplicate_count > 0:
        findings.append(
            {
                "code": "duplicate_rows",
                "column": None,
                "count": duplicate_count,
                "message": (
                    f"Dataset contains {duplicate_count} repeated row(s) "
                    "after their first occurrence."
                ),
            }
        )

    for name in df.columns:
        series = df[name]
        text = series.astype("string")

        # Calculate each measurement once.
        missing_count = int(series.isna().sum())
        blank_count = int(
            text.str.fullmatch(r"\s*", na=False).sum()
        )
        placeholder_count = int(
            text.str.strip()
            .str.casefold()
            .isin(PLACEHOLDER_VALUES)
            .sum()
        )

        columns.append(
            {
                "name": str(name),
                "dtype": str(series.dtype),
                "missing_count": missing_count,
                "missing_percent": round(
                    missing_count / row_count * 100, 2
                ),
                "blank_count": blank_count,
                "placeholder_count": placeholder_count,
                "unique_count": int(series.nunique(dropna=True)),
            }
        )

        # Generate findings from the measurements above.
        checks = [
            ("missing_values", missing_count, "missing"),
            ("blank_values", blank_count, "whitespace-only"),
            (
                "placeholder_values",
                placeholder_count,
                "potential placeholder",
            ),
        ]

        for code, count, description in checks:
            if count > 0:
                findings.append(
                    {
                        "code": code,
                        "column": str(name),
                        "count": count,
                        "message": (
                            f"Column '{name}' contains "
                            f"{count} {description} value(s)."
                        ),
                    }
                )

    return {
        "row_count": row_count,
        "column_count": int(df.shape[1]),
        "duplicate_row_count": duplicate_count,
        "duplicate_row_percent": duplicate_percent,
        "columns": columns,
        "findings": findings,
    }