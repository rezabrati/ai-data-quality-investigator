from ai_data_quality_investigator.profiling import read_csv_dataframe
import numpy as np
import pandas as pd


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

def numeric_distribution(
    content: bytes,
    column: str,
    bins: int = 20,
) -> dict[str, object]:
    """Calculate histogram bins and box-plot statistics."""
    if not 1 <= bins <= 100:
        raise ValueError("Bins must be between 1 and 100.")

    df = read_csv_dataframe(content)

    if column not in df.columns:
        raise ValueError(f"Column '{column}' does not exist.")

    series = df[column]

    if (
        not pd.api.types.is_numeric_dtype(series)
        or pd.api.types.is_bool_dtype(series)
    ):
        raise ValueError(f"Column '{column}' is not numeric.")

    values = series.dropna().to_numpy(dtype=float)
    finite = values[np.isfinite(values)]

    if finite.size == 0:
        raise ValueError("The column has no finite numeric values.")

    counts, edges = np.histogram(finite, bins=bins)

    q1, median, q3 = np.quantile(finite, [0.25, 0.5, 0.75])
    iqr = float(q3 - q1)

    boxplot = {
        "q1": float(q1),
        "median": float(median),
        "q3": float(q3),
    }

    if iqr > 0:
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr

        inside = finite[
            (finite >= lower_fence) & (finite <= upper_fence)
        ]

        boxplot.update({
            "status": "available",
            "whisker_method": "1.5_iqr",
            "lower_whisker": float(inside.min()),
            "upper_whisker": float(inside.max()),
            "outlier_count": int(finite.size - inside.size),
        })
    else:
        # Match our existing policy for zero-IQR columns.
        boxplot.update({
            "status": "skipped",
            "reason": "IQR is zero.",
        })

    return {
        "column": column,
        "finite_count": int(finite.size),
        "missing_count": int(series.isna().sum()),
        "infinite_count": int(values.size - finite.size),
        "histogram": [
            {
                "lower": float(edges[index]),
                "upper": float(edges[index + 1]),
                "count": int(count),
            }
            for index, count in enumerate(counts)
        ],
        "boxplot": boxplot,
    }