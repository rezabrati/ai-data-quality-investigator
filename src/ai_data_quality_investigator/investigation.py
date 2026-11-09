from ai_data_quality_investigator.profiling import read_csv_dataframe


def category_frequencies(
    content: bytes,
    column: str,
    limit: int = 10,
) -> dict[str, object]:
    """Count values without changing case, spaces, or categories."""
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50.")

    df = read_csv_dataframe(content)

    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist.")

    series = df[column]
    non_missing = series.dropna()
    counts = non_missing.value_counts()
    top_counts = counts.head(limit)

    return {
        "column": column,
        "row_count": len(df),
        "missing_count": int(series.isna().sum()),
        "non_missing_count": len(non_missing),
        "unique_count": int(len(counts)),
        "percent_basis": "non-missing rows",
        "categories": [
            {
                "value": str(value),
                "count": int(count),
                "percent": round(
                    int(count) / len(non_missing) * 100,
                    2,
                ),
            }
            for value, count in top_counts.items()
        ],
        "other_count": int(counts.iloc[limit:].sum()),
    }