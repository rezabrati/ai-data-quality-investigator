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


def compare_target_by_category(
    content: bytes,
    column: str,
    target_column: str,
    limit: int = 10,
) -> dict[str, object]:
    """Compare class distributions within categorical feature values."""
    if not 1 <= limit <= 50:
        raise ValueError("Limit must be between 1 and 50.")

    if column == target_column:
        raise ValueError("Feature and target must be different columns.")

    df = read_csv_dataframe(content)

    for name in (column, target_column):
        if name not in df.columns:
            raise ValueError(f"Column '{name}' does not exist.")

    if (
        pd.api.types.is_numeric_dtype(df[column])
        and not pd.api.types.is_bool_dtype(df[column])
    ):
        raise ValueError(
            "This check supports categorical features. "
            "Numeric features need a separate comparison."
        )

    # Analyze only rows where both values are present.
    paired = df[[column, target_column]].dropna()

    if paired.empty:
        raise ValueError(
            "No rows contain both a feature value and a target label."
        )

    classes = paired[target_column].value_counts().index.tolist()

    # Bound the response size for this first classification check.
    if len(classes) > 20:
        raise ValueError(
            "This check supports classification targets "
            "with at most 20 classes."
        )

    category_counts = paired[column].value_counts()
    groups = []

    for category, count in category_counts.head(limit).items():
        group = paired.loc[
            paired[column] == category,
            target_column,
        ]
        target_counts = group.value_counts()
        group_size = int(count)

        groups.append({
            "value": str(category),
            "row_count": group_size,
            "target_distribution": [
                {
                    "value": str(label),
                    "count": int(target_counts.get(label, 0)),
                    "percent": round(
                        int(target_counts.get(label, 0))
                        / group_size * 100,
                        2,
                    ),
                }
                for label in classes
            ],
        })

    return {
        "column": column,
        "target_column": target_column,
        "row_count": int(len(df)),
        "analyzed_count": int(len(paired)),
        "excluded_missing_count": int(len(df) - len(paired)),
        "category_count": int(len(category_counts)),
        "percent_basis": "rows within each displayed category",
        "groups": groups,
        "other_count": int(category_counts.iloc[limit:].sum()),
    }