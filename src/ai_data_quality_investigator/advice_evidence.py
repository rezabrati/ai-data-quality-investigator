import json
import re


def build_evidence_catalog(
    profile: dict,
    comparison: dict | None,
    duckdb_comparisons: list[dict],
) -> dict:
    catalog = {}
    summary = profile["summary"]

    def add(evidence_id, fact, coverage_id=None):
        catalog[evidence_id] = {
            "fact": fact,
            "coverage_id": coverage_id,
        }

    add(
        "PROFILE",
        f"Rows: {summary['row_count']}; "
        f"columns: {summary['column_count']}; "
        f"duplicate rows: {summary['duplicate_row_count']}.",
    )

    for index, column in enumerate(summary["columns"], start=1):
        name = json.dumps(column["name"], ensure_ascii=False)

        fact = (
            f"Column {name}: "
            f"missing={column['missing_count']}; "
            f"blank={column['blank_count']}; "
            f"potential placeholders={column['placeholder_count']}; "
            f"unique values={column['unique_count']}."
        )

        numeric = column.get("numeric_summary")

        if numeric:
            outliers = numeric.get("outliers", {})

            if "count" in outliers:
                fact += (
                    f" Potential IQR outliers={outliers['count']} "
                    f"({outliers['percent']:.2f}% of finite values)."
                )

        add(f"COLUMN-{index}", fact)

    target = summary.get("target_summary")

    if target:
        for index, item in enumerate(
            target.get("class_distribution", []),
            start=1,
        ):
            add(
                f"TARGET-CLASS-{index}",
                f"Target {json.dumps(target['column'])}, "
                f"class {json.dumps(item['value'])}: "
                f"{item['count']} labeled rows "
                f"({item['percent']:.2f}%).",
            )

    if comparison:
        coverage_id = "TARGET-COVERAGE"

        add(
            coverage_id,
            f"Comparison of {json.dumps(comparison['column'])} "
            f"with target {json.dumps(comparison['target_column'])}: "
            f"analyzed rows={comparison['analyzed_count']}; "
            f"excluded missing rows="
            f"{comparison['excluded_missing_count']}; "
            f"rows in unlisted groups={comparison['other_count']}.",
        )

        for index, group in enumerate(
            comparison["groups"],
            start=1,
        ):
            distribution = "; ".join(
                f"{json.dumps(item['value'])}: "
                f"{item['count']}/{group['row_count']} "
                f"({item['percent']:.2f}%)"
                for item in group["target_distribution"]
            )

            add(
                f"TARGET-GROUP-{index}",
                f"{json.dumps(comparison['column'])}="
                f"{json.dumps(group['value'])}; "
                f"target distribution: {distribution}.",
                coverage_id,
            )

    for query_index, query in enumerate(
        duckdb_comparisons,
        start=1,
    ):
        prefix = f"DUCKDB-{query_index}"
        coverage_id = f"{prefix}-COVERAGE"

        add(
            coverage_id,
            f"Grouping columns="
            f"{json.dumps(query['grouping_columns'])}; "
            f"analyzed rows={query['analyzed_count']}; "
            f"excluded missing rows="
            f"{query['excluded_missing_count']}; "
            f"total groups={query['group_count']}; "
            f"displayed groups={len(query['groups'])}; "
            f"rows in unlisted groups={query['other_count']}.",
        )

        for group_index, group in enumerate(
            query["groups"],
            start=1,
        ):
            add(
                f"{prefix}-GROUP-{group_index}",
                f"Group {json.dumps(group['values'], ensure_ascii=False)}: "
                f"target {json.dumps(query['target_column'])}="
                f"{json.dumps(query['target_value'])} in "
                f"{group['target_count']}/{group['row_count']} rows "
                f"({group['target_percent']:.2f}% within this group).",
                coverage_id,
            )

    return catalog


def parse_advice(text: str, catalog: dict) -> list[dict]:
    data = json.loads(text)

    if not isinstance(data, dict) or set(data) != {"suggestions"}:
        raise ValueError("Expected a suggestions object.")

    suggestions = data["suggestions"]

    if (
        not isinstance(suggestions, list)
        or not 1 <= len(suggestions) <= 3
    ):
        raise ValueError("Expected one to three suggestions.")

    for item in suggestions:
        if (
            not isinstance(item, dict)
            or set(item) != {"question", "reason", "evidence_ids"}
        ):
            raise ValueError("Invalid suggestion fields.")

        for field in ("question", "reason"):
            if (
                not isinstance(item[field], str)
                or not 1 <= len(item[field].strip()) <= 1000
            ):
                raise ValueError("Invalid suggestion text.")

        ids = item["evidence_ids"]

        if not isinstance(ids, list) or not 1 <= len(ids) <= 3:
            raise ValueError(
                "Expected one to three evidence references."
            )

        if any(
            not isinstance(ref, str) or ref not in catalog
            for ref in ids
        ):
            raise ValueError("Unknown evidence reference.")

        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate evidence reference.")

    has_duckdb = any(
        key.startswith("DUCKDB-") and "-GROUP-" in key
        for key in catalog
    )

    cites_duckdb = any(
        ref.startswith("DUCKDB-") and "-GROUP-" in ref
        for item in suggestions
        for ref in item["evidence_ids"]
    )

    if has_duckdb and not cites_duckdb:
        raise ValueError(
            "Advice did not reference a DuckDB group."
        )

    return suggestions


def render_advice(suggestions: list[dict], catalog: dict) -> str:
    sections = []

    for index, item in enumerate(suggestions, start=1):
        references = list(item["evidence_ids"])

        # Include coverage whenever a comparison group is cited.
        for ref in item["evidence_ids"]:
            coverage_id = catalog[ref]["coverage_id"]

            if coverage_id and coverage_id not in references:
                references.append(coverage_id)

        facts = "\n".join(
            f"{ref}: {catalog[ref]['fact']}"
            for ref in references
        )

        # Keep dataset values inside a plain-text Markdown block.
        longest = max(
            (len(run) for run in re.findall(r"`+", facts)),
            default=0,
        )
        fence = "`" * max(3, longest + 1)

        sections.append(
            f"**{index}. {item['question'].strip()}**\n\n"
            f"{item['reason'].strip()}\n\n"
            f"Supporting tool evidence:\n\n"
            f"{fence}text\n{facts}\n{fence}"
        )

    return "\n\n".join(sections)