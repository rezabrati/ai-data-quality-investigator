def render_profile_facts(profile: dict) -> str:
    """Render tool-provided statistics without LLM interpretation."""
    summary = profile["summary"]

    lines = [
        "DATASET FACTS",
        f"Dataset ID: {profile['dataset_id']}",
        f"Rows: {summary['row_count']}",
        f"Columns: {summary['column_count']}",
        (
            f"Duplicate rows: {summary['duplicate_row_count']} "
            f"({summary['duplicate_row_percent']}%)"
        ),
    ]

    target = summary.get("target_summary")

    if target is not None:
        lines.extend([
            f"Target: {target['column']}",
            f"Task: {target['task_type']}",
            f"Missing targets: {target['missing_count']}",
        ])

        for label in target.get("class_distribution", []):
            lines.append(
                f"Class {label['value']!r}: "
                f"{label['count']} labeled rows "
                f"({label['percent']}%)"
            )

    for column in summary["columns"]:
        lines.extend([
            "",
            f"Column: {column['name']}",
            f"Inferred type: {column['dtype']}",
            f"Missing: {column['missing_count']}",
            f"Blank: {column['blank_count']}",
            f"Placeholder: {column['placeholder_count']}",
            f"Unique non-missing values: {column['unique_count']}",
        ])

        numeric = column.get("numeric_summary")

        if numeric is not None:
            for field in (
                "min", "max", "mean", "median",
                "std", "q1", "q3", "skewness",
                "finite_count", "infinite_count",
            ):
                value = numeric.get(field)
                display = "unavailable" if value is None else value
                lines.append(f"{field}: {display}")

            outliers = numeric.get("outliers", {})

            if outliers.get("status") == "skipped":
                lines.append(
                    f"IQR outliers: skipped ({outliers['reason']})"
                )
            elif "count" in outliers:
                lines.append(
                    f"IQR outliers: {outliers['count']} "
                    f"({outliers['percent']}% of finite values)"
                )

    lines.extend([
        "",
        f"Findings reported: {len(summary['findings'])}",
    ])

    for finding in summary["findings"]:
        lines.append(f"- {finding['message']}")

    return "\n".join(lines)