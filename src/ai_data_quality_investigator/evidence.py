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