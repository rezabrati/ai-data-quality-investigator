import asyncio
import json
import os
from uuid import UUID

from mcp import Client


def quote_identifier(value: str) -> str:
    """Quote a column name for DuckDB."""
    return '"' + value.replace('"', '""') + '"'


def quote_literal(value: str) -> str:
    """Quote a string value for DuckDB."""
    return "'" + value.replace("'", "''") + "'"


class DatasetSQLQueries:
    """Run bounded categorical comparisons for one verified dataset."""

    def __init__(self, dataset_id: str, verified_profile: dict):
        self.dataset_id = str(UUID(dataset_id))

        if verified_profile.get("dataset_id") != self.dataset_id:
            raise ValueError("Profile does not match the dataset.")

        self.summary = verified_profile["summary"]
        self.columns = {
            column["name"]: column
            for column in self.summary["columns"]
        }

        self.url = os.getenv(
            "DUCKDB_MCP_URL",
            "http://127.0.0.1:8002/mcp",
        )

        self.calls_used = 0
        self.evidence: list[dict] = []
        self.activity: list[dict] = []

    async def compare(
        self,
        columns: list[str],
        target_value: str,
    ) -> dict:
        """Compare a target-class percentage across one or two columns."""
        if self.calls_used >= 2:
            raise ValueError(
                "DuckDB has reached its limit of two calls "
                "per investigation."
            )

        # Reserve before awaiting. Failed attempts also use the budget.
        self.calls_used += 1

        if not 1 <= len(columns) <= 2:
            raise ValueError("Choose one or two grouping columns.")

        if len(set(columns)) != len(columns):
            raise ValueError("Grouping columns must be different.")

        target = self.summary.get("target_summary")

        if not target or target.get("task_type") != "classification":
            raise ValueError(
                "This tool requires a classification target."
            )

        target_column = target["column"]
        distribution = target.get("class_distribution", [])

        if not 2 <= len(distribution) <= 20:
            raise ValueError(
                "The target must have between 2 and 20 classes."
            )

        allowed_values = [
            item["value"]
            for item in distribution
            if isinstance(item["value"], str)
        ]

        if target_value not in allowed_values:
            raise ValueError(
                "Choose a string target class from the profile."
            )

        for name in columns:
            column = self.columns.get(name)

            if column is None:
                raise ValueError(f"Unknown column: {name}")

            if name == target_column:
                raise ValueError(
                    "The target cannot be a grouping column."
                )

            if column.get("numeric_summary") is not None:
                raise ValueError(
                    f"Choose a categorical column instead of {name}."
                )

            if not 2 <= column["unique_count"] <= 20:
                raise ValueError(
                    f"{name} must have between 2 and 20 unique values."
                )

        # The dataset path comes from the validated UUID.
        path = f"/datasets/{self.dataset_id}.csv"

        identifiers = [quote_identifier(name) for name in columns]
        target_identifier = quote_identifier(target_column)

        selected_columns = ", ".join(
            f"{identifier} AS group_{index}"
            for index, identifier in enumerate(identifiers, start=1)
        )

        group_positions = ", ".join(
            str(index)
            for index in range(1, len(columns) + 1)
        )

        non_missing = " AND ".join(
            f"{identifier} IS NOT NULL"
            for identifier in [*identifiers, target_identifier]
        )

        sql = f"""
            SELECT
                {selected_columns},
                COUNT(*) AS group_rows,
                COUNT(*) FILTER (
                    WHERE {target_identifier}
                        = {quote_literal(target_value)}
                ) AS target_rows,
                SUM(COUNT(*)) OVER () AS analyzed_rows,
                COUNT(*) OVER () AS total_groups
            FROM read_csv_auto(
                {quote_literal(path)},
                header = true,
                all_varchar = true
            )
            WHERE {non_missing}
            GROUP BY {group_positions}
            ORDER BY group_rows DESC, {group_positions}
            LIMIT 20
        """

        activity = {
            "name": "duckdb_compare_target_by_columns",
            "arguments": {
                "columns": list(columns),
                "target_value": target_value,
            },
            "status": "requested",
        }
        self.activity.append(activity)

        try:
            async with asyncio.timeout(25):
                async with Client(self.url) as client:
                    result = await client.call_tool(
                        "execute_query",
                        {"sql": sql},
                    )

            if result.is_error:
                raise ValueError("DuckDB returned a tool error.")

            text = next(
                block.text
                for block in result.content
                if block.type == "text"
            )
            data = json.loads(text)

            expected_columns = [
                *[
                    f"group_{index}"
                    for index in range(1, len(columns) + 1)
                ],
                "group_rows",
                "target_rows",
                "analyzed_rows",
                "total_groups",
            ]

            if (
                data.get("success") is not True
                or data.get("columns") != expected_columns
            ):
                raise ValueError("Unexpected DuckDB response.")

            rows = data.get("rows")

            if not isinstance(rows, list) or not rows:
                raise ValueError(
                    "No groups with non-missing values were returned."
                )

            if len(rows) > 20:
                raise ValueError("Too many groups returned.")

            groups = []
            analyzed_count = None
            group_count = None

            for row in rows:
                if not isinstance(row, list) or len(row) != len(
                    expected_columns
                ):
                    raise ValueError("Invalid result row.")

                labels = row[:len(columns)]
                count, matches, analyzed, total_groups = row[len(columns):]

                if any(
                    type(value) is not int
                    for value in [count, matches, analyzed, total_groups]
                ):
                    raise ValueError("Invalid counts returned.")

                if not (
                    0 <= matches <= count <= analyzed
                    <= self.summary["row_count"]
                    and count > 0
                    and total_groups >= len(rows)
                ):
                    raise ValueError("Inconsistent counts returned.")

                if not all(isinstance(label, str) for label in labels):
                    raise ValueError("Invalid grouping values.")

                if analyzed_count is None:
                    analyzed_count = analyzed
                    group_count = total_groups
                elif (
                    analyzed != analyzed_count
                    or total_groups != group_count
                ):
                    raise ValueError("Inconsistent group totals.")

                groups.append({
                    "values": dict(zip(columns, labels)),
                    "row_count": count,
                    "target_count": matches,
                    "target_percent": round(
                        100.0 * matches / count,
                        2,
                    ),
                })

            displayed_count = sum(
                group["row_count"] for group in groups
            )

            if (
                displayed_count > analyzed_count
                or (
                    group_count <= 20
                    and displayed_count != analyzed_count
                )
            ):
                raise ValueError("Group counts do not match totals.")

            evidence = {
                "dataset_id": self.dataset_id,
                "grouping_columns": list(columns),
                "target_column": target_column,
                "target_value": target_value,
                "row_count": self.summary["row_count"],
                "analyzed_count": analyzed_count,
                "excluded_missing_count": (
                    self.summary["row_count"] - analyzed_count
                ),
                "group_count": group_count,
                "percent_basis": (
                    "rows within each displayed group"
                ),
                "groups": groups,
                "other_count": analyzed_count - displayed_count,
            }

            self.evidence.append(evidence)
            activity["status"] = "succeeded"

            return evidence

        except Exception:
            activity["status"] = "failed"
            raise