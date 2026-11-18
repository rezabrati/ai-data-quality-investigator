import json


def extract_verified_profile(items: list, dataset_id: str) -> dict | None:
    """Find a matching profiling call and structurally valid result."""
    profile_call_ids = set()
    verified_profile = None

    for item in items:
        if item.type == "tool_call_item":
            call = item.raw_item

            if call.name != "profile_dataset":
                continue

            try:
                arguments = json.loads(call.arguments)
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(arguments, dict):
                continue

            if arguments.get("dataset_id") == dataset_id:
                profile_call_ids.add(call.call_id)

        elif item.type == "tool_call_output_item":
            if item.raw_item.get("call_id") not in profile_call_ids:
                continue

            output = item.output

            if not isinstance(output, dict):
                continue

            if output.get("type") != "text":
                continue

            try:
                profile = json.loads(output.get("text", ""))
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(profile, dict):
                continue

            summary = profile.get("summary")

            if (
                profile.get("dataset_id") == dataset_id
                and isinstance(summary, dict)
                and isinstance(summary.get("columns"), list)
                and isinstance(summary.get("findings"), list)
                and type(summary.get("row_count")) is int
                and type(summary.get("column_count")) is int
            ):
                verified_profile = profile

    return verified_profile

def extract_verified_categories(
    items: list,
    dataset_id: str,
    row_count: int,
) -> dict | None:
    """Find a category result matching its call and dataset."""
    category_calls = {}
    verified_categories = None

    for item in items:
        if item.type == "tool_call_item":
            call = item.raw_item

            if call.name != "get_category_frequencies":
                continue

            try:
                arguments = json.loads(call.arguments)
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(arguments, dict):
                continue

            column = arguments.get("column")

            if (
                arguments.get("dataset_id") == dataset_id
                and isinstance(column, str)
            ):
                category_calls[call.call_id] = column

        elif item.type == "tool_call_output_item":
            call_id = item.raw_item.get("call_id")

            if call_id not in category_calls:
                continue

            output = item.output

            if not isinstance(output, dict):
                continue

            if output.get("type") != "text":
                continue

            try:
                frequencies = json.loads(output.get("text", ""))
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(frequencies, dict):
                continue

            if (
                frequencies.get("dataset_id") == dataset_id
                and frequencies.get("column") == category_calls[call_id]
                and frequencies.get("row_count") == row_count
                and isinstance(frequencies.get("categories"), list)
            ):
                verified_categories = frequencies

    return verified_categories

def extract_verified_comparison(
    items: list,
    dataset_id: str,
    profile: dict,
) -> dict | None:
    """Match comparison evidence to its tool call and dataset profile."""
    summary = profile["summary"]
    target = summary.get("target_summary")

    if not target or target.get("task_type") != "classification":
        return None

    columns = {column["name"] for column in summary["columns"]}
    comparison_calls = {}
    verified_comparison = None

    for item in items:
        if item.type == "tool_call_item":
            call = item.raw_item

            if call.name != "compare_target_by_category":
                continue

            try:
                arguments = json.loads(call.arguments)
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(arguments, dict):
                continue

            column = arguments.get("column")

            if (
                arguments.get("dataset_id") == dataset_id
                and isinstance(column, str)
                and column in columns
                and column != target["column"]
            ):
                comparison_calls[call.call_id] = column

        elif item.type == "tool_call_output_item":
            call_id = item.raw_item.get("call_id")

            if call_id not in comparison_calls:
                continue

            output = item.output

            # Our current MCP integration returns JSON in a text block.
            if not isinstance(output, dict):
                continue

            if output.get("type") != "text":
                continue

            try:
                comparison = json.loads(output.get("text", ""))
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(comparison, dict):
                continue

            if (
                comparison.get("dataset_id") == dataset_id
                and comparison.get("column") == comparison_calls[call_id]
                and comparison.get("target_column") == target["column"]
                and type(comparison.get("row_count")) is int
                and comparison["row_count"] == summary["row_count"]
                and isinstance(comparison.get("groups"), list)
            ):
                verified_comparison = comparison

    return verified_comparison