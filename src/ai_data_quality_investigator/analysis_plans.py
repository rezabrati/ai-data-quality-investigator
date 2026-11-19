import json

from ai_data_quality_investigator.advice_evidence import parse_advice


METHODS = {
    "compare_target_rates",
    "estimate_rate_intervals",
    "test_target_association",
    "compare_outlier_target_rates",
    "review_column_meaning",
}


def analysis_key(method: str, columns: list[str]) -> tuple:
    # Reversing column order does not create a new analysis.
    return method, tuple(sorted(columns))


def build_completed_analyses(
    comparison: dict | None,
    duckdb_comparisons: list[dict],
) -> list[dict]:
    completed = []

    if comparison:
        completed.append({
            "method": "compare_target_rates",
            "columns": [comparison["column"]],
        })

    for query in duckdb_comparisons:
        completed.append({
            "method": "compare_target_rates",
            "columns": list(query["grouping_columns"]),
        })

    return completed


def parse_planned_advice(
    text: str,
    catalog: dict,
    completed: list[dict],
    summary: dict,
) -> list[dict]:
    data = json.loads(text)

    if not isinstance(data, dict) or set(data) != {"suggestions"}:
        raise ValueError("Expected a suggestions object.")

    proposals = data["suggestions"]

    if (
        not isinstance(proposals, list)
        or not 1 <= len(proposals) <= 3
    ):
        raise ValueError("Expected one to three proposals.")

    known_columns = {
        column["name"]: column
        for column in summary["columns"]
    }

    completed_keys = {
        analysis_key(item["method"], item["columns"])
        for item in completed
    }

    proposed_keys = set()
    normalized = []

    target = summary.get("target_summary")
    target_name = target["column"] if target else None

    for proposal in proposals:
        if (
            not isinstance(proposal, dict)
            or set(proposal) != {
                "method",
                "columns",
                "reason",
                "evidence_ids",
            }
        ):
            raise ValueError("Invalid proposal fields.")

        method = proposal["method"]
        columns = proposal["columns"]

        if not isinstance(method, str) or method not in METHODS:
            raise ValueError("Unknown analysis method.")

        if (
            not isinstance(columns, list)
            or not 1 <= len(columns) <= 2
            or any(
                not isinstance(name, str)
                or name not in known_columns
                for name in columns
            )
        ):
            raise ValueError("Choose one or two known columns.")

        if len(set(columns)) != len(columns):
            raise ValueError("Duplicate column names.")

        key = analysis_key(method, columns)

        if key in completed_keys:
            raise ValueError("This analysis was already completed.")

        if key in proposed_keys:
            raise ValueError("Repeated proposal.")

        proposed_keys.add(key)

        if method != "review_column_meaning":
            if (
                not target
                or target.get("task_type") != "classification"
            ):
                raise ValueError(
                    "This method requires a classification target."
                )

            if target_name in columns:
                raise ValueError(
                    "Do not include the target as a feature."
                )

        if method in {
            "compare_target_rates",
            "estimate_rate_intervals",
            "test_target_association",
        }:
            for name in columns:
                column = known_columns[name]

                if (
                    column.get("numeric_summary") is not None
                    or not 2 <= column["unique_count"] <= 20
                ):
                    raise ValueError(
                        "Choose categorical features with "
                        "two to twenty unique values."
                    )

        if method == "estimate_rate_intervals":
            if len(target.get("class_distribution", [])) != 2:
                raise ValueError(
                    "This version supports rate intervals "
                    "for binary targets."
                )

        if method == "compare_outlier_target_rates":
            if len(columns) != 1:
                raise ValueError("Choose one numeric feature.")

            numeric = known_columns[columns[0]].get(
                "numeric_summary"
            )
            outliers = numeric.get("outliers", {}) if numeric else {}

            if outliers.get("count", 0) <= 0:
                raise ValueError(
                    "Choose a numeric feature with reported "
                    "potential IQR outliers."
                )

        if method == "review_column_meaning" and len(columns) != 1:
            raise ValueError("Review one column at a time.")

        names = ", ".join(
            json.dumps(name, ensure_ascii=False)
            for name in columns
        )
        target_label = json.dumps(target_name, ensure_ascii=False)

        if method == "compare_target_rates":
            question = (
                f"How do {target_label} class proportions vary "
                f"across groups defined by {names}?"
            )
        elif method == "estimate_rate_intervals":
            question = (
                f"How wide are confidence intervals for "
                f"{target_label} class proportions across "
                f"groups defined by {names}?"
            )
        elif method == "test_target_association":
            question = (
                f"Does an association test appropriate to the "
                f"group counts support an association between "
                f"{names} and {target_label}?"
            )
        elif method == "compare_outlier_target_rates":
            question = (
                f"How do {target_label} class proportions differ "
                f"between potential IQR outliers and other "
                f"finite observations in {names}?"
            )
        else:
            question = (
                f"How does the dataset documentation define "
                f"{names} and its recorded categories or codes?"
            )

        normalized.append({
            "question": question,
            "reason": proposal["reason"],
            "evidence_ids": proposal["evidence_ids"],
        })

    # Reuse your existing text and evidence-reference validation.
    validated = parse_advice(
        json.dumps({"suggestions": normalized}),
        catalog,
    )

    for item, proposal in zip(validated, proposals):
        item["method"] = proposal["method"]
        item["columns"] = proposal["columns"]
        item["status"] = "proposed"

    return validated