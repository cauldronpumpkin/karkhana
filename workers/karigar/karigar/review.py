from __future__ import annotations


def build_review_report(*, task_title: str, branch_name: str, changed_files: list[str], verification_results: list[dict[str, object]], logs_path: str, diff_path: str | None, next_recommendation: str, graphify_required: bool) -> str:
    lines = [
        "# Karigar Review Report",
        f"- Task: {task_title}",
        f"- Branch: {branch_name}",
        f"- Changed files: {', '.join(changed_files) if changed_files else 'none'}",
        f"- Logs path: {logs_path}",
        f"- Diff path: {diff_path or 'n/a'}",
        f"- Graphify update required: {'yes' if graphify_required else 'no'}",
        "",
        "## Verification Results",
    ]
    for item in verification_results:
        lines.append(f"- {item.get('command')}: {item.get('status')} — {item.get('summary')}")
    lines.extend(["", "## Next Recommendation", f"- {next_recommendation}", "", "Human approval required before merge."])
    return "\n".join(lines) + "\n"
