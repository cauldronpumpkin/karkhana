from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


REQUIRED_FRONTMATTER_FIELDS = frozenset({
    "run_id",
    "title",
    "status",
    "stage",
    "created_at",
    "updated_at",
})

LEDGER_POLICIES = frozenset({"none", "read_only", "required", "strict"})

COMPACT_CONTEXT_SECTIONS = (
    "Current goal",
    "Decisions",
    "Risks",
    "Next actions",
    "Artifacts",
    "Reusable lessons",
)


class FactoryRunLedgerError(ValueError):
    pass


def validate_ledger_policy(policy: str | None) -> str:
    normalized = (policy or "none").strip().lower()
    if normalized not in LEDGER_POLICIES:
        raise FactoryRunLedgerError(f"Invalid ledger_policy: {policy}")
    return normalized


def resolve_repo_relative_ledger_path(
    ledger_path: str | os.PathLike[str] | None,
    repo_root: str | os.PathLike[str] = ".",
) -> str | None:
    if ledger_path is None:
        return None
    raw_path = os.fspath(ledger_path).strip()
    if not raw_path:
        return None

    normalized = raw_path.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("~") or ":" in normalized.split("/", 1)[0]:
        raise FactoryRunLedgerError("ledger_path must be a relative path")

    parts: list[str] = []
    for part in normalized.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise FactoryRunLedgerError("ledger_path must not contain traversal segments")
        parts.append(part)

    relative_path = "/".join(parts) or None
    if not relative_path:
        return None

    root = Path(repo_root).resolve()
    resolved = (root / relative_path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise FactoryRunLedgerError("ledger_path must stay within repo_root") from exc
    return relative_path


def validate_ledger_metadata(
    metadata: dict[str, Any] | None = None,
    *,
    ledger_path: str | os.PathLike[str] | None = None,
    ledger_policy: str | None = None,
) -> dict[str, str | None]:
    data = dict(metadata or {})
    policy = validate_ledger_policy(ledger_policy if ledger_policy is not None else data.get("ledger_policy"))
    path_value = ledger_path if ledger_path is not None else data.get("ledger_path")
    path = resolve_repo_relative_ledger_path(path_value)
    if policy != "none" and not path:
        raise FactoryRunLedgerError("ledger_path is required when ledger_policy is not 'none'")
    return {"ledger_policy": policy, "ledger_path": path}


def extract_compact_ledger_context(
    ledger_path: str | os.PathLike[str] | None,
    *,
    repo_root: str | os.PathLike[str] = ".",
    max_chars: int = 6000,
) -> dict[str, Any]:
    relative_path = resolve_repo_relative_ledger_path(ledger_path)
    if not relative_path:
        return {}

    root = Path(repo_root).resolve()
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise FactoryRunLedgerError("ledger_path must stay within repo_root") from exc
    if not path.exists():
        return {
            "ledger_path": relative_path,
            "available": False,
            "warning": f"Ledger not found: {relative_path}",
        }

    parsed = FactoryRunLedgerService(base_dir=path.parent).parse_text(path.read_text(encoding="utf-8"))
    body = parsed["body"]
    sections: dict[str, str] = {}
    remaining_chars = max(max_chars, 0)
    for heading in COMPACT_CONTEXT_SECTIONS:
        section = _extract_section(body, heading).strip()
        if not section:
            sections[heading] = ""
            continue
        excerpt = section[:remaining_chars].rstrip() if remaining_chars else ""
        sections[heading] = excerpt
        remaining_chars = max(0, remaining_chars - len(excerpt))

    return {
        "ledger_path": relative_path,
        "available": True,
        "frontmatter": parsed["metadata"],
        "run_id": parsed["run_id"],
        "title": parsed["title"],
        "status": parsed["status"],
        "stage": parsed["stage"],
        "updated_at": parsed["updated_at"],
        "sections": sections,
        "truncated": any(len(_extract_section(body, heading).strip()) > len(sections[heading]) for heading in COMPACT_CONTEXT_SECTIONS),
    }


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "run"


def _escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|")


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    result = yaml.safe_load(text)
    if result is None:
        return {}
    if not isinstance(result, dict):
        raise FactoryRunLedgerError("YAML frontmatter must be a mapping")
    return result


def _format_frontmatter(metadata: dict[str, Any]) -> str:
    return "---\n" + yaml.dump(metadata, default_flow_style=False, sort_keys=False) + "---\n"


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    text = text.strip()
    if not text.startswith("---"):
        raise FactoryRunLedgerError("Missing frontmatter delimiter '---'")

    end_idx = text.find("---", 3)
    if end_idx == -1:
        raise FactoryRunLedgerError("Unclosed frontmatter delimiter '---'")

    frontmatter_text = text[3:end_idx].strip()
    body = text[end_idx + 3:].strip()

    metadata = _parse_simple_yaml(frontmatter_text)
    return metadata, body


def _validate_required(metadata: dict[str, Any]) -> None:
    missing = REQUIRED_FRONTMATTER_FIELDS - set(metadata.keys())
    if missing:
        raise FactoryRunLedgerError(
            f"Missing required frontmatter field(s): {', '.join(sorted(missing))}"
        )
    # Strict type validation for required fields
    for field in ("run_id", "title", "status", "stage", "created_at", "updated_at"):
        value = metadata.get(field)
        if not isinstance(value, str):
            raise FactoryRunLedgerError(
                f"Required frontmatter field '{field}' must be a string, got {type(value).__name__}"
            )
        if not value.strip():
            raise FactoryRunLedgerError(
                f"Required frontmatter field '{field}' must not be empty"
            )


def _touch_updated_at(metadata: dict[str, Any]) -> dict[str, Any]:
    metadata["updated_at"] = _utcnow_iso()
    return metadata


def _find_heading_line(lines: list[str], heading: str) -> int | None:
    pattern = re.compile(r"^#+\s+" + re.escape(heading) + r"\s*$")
    for i, line in enumerate(lines):
        if pattern.match(line):
            return i
    return None


def _extract_section(body: str, heading: str) -> str:
    lines = body.split("\n")
    heading_idx = _find_heading_line(lines, heading)
    if heading_idx is None:
        return ""
    collected: list[str] = []
    for line in lines[heading_idx + 1:]:
        if line.startswith("## "):
            break
        collected.append(line)
    return "\n".join(collected).strip()


def _append_table_row(body: str, heading: str, row: list[str]) -> str:
    lines = body.split("\n")
    heading_idx = _find_heading_line(lines, heading)
    if heading_idx is None:
        table = "| " + " | ".join(row) + " |"
        return body.rstrip() + f"\n\n## {heading}\n\n| {(' | '.join([''] * len(row)))} |\n|---|---|---|\n{table}\n"

    sep_idx: int | None = None
    last_data_idx: int | None = None
    for i in range(heading_idx + 1, len(lines)):
        stripped = lines[i].rstrip()
        if stripped == "":
            if last_data_idx is not None:
                break
            continue
        if stripped.startswith("|") and stripped.replace("-", "").replace("|", "").replace(" ", "").replace(":", "") == "":
            sep_idx = i
            continue
        if stripped.startswith("|"):
            last_data_idx = i
            continue
        if last_data_idx is not None:
            break

    insert_idx = (last_data_idx + 1) if last_data_idx is not None else (heading_idx + 1)
    if insert_idx >= len(lines):
        lines.append("")
        insert_idx = len(lines) - 1

    escaped = [_escape_table_cell(cell) for cell in row]
    table_line = "| " + " | ".join(escaped) + " |"
    lines.insert(insert_idx, table_line)
    return "\n".join(lines)


def _append_bullet(body: str, heading: str, bullet_text: str) -> str:
    lines = body.split("\n")
    heading_idx = _find_heading_line(lines, heading)
    if heading_idx is None:
        return body.rstrip() + f"\n\n## {heading}\n\n- {bullet_text}\n"

    insert_idx: int | None = None
    for i in range(heading_idx + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped == "":
            if insert_idx is None:
                insert_idx = i
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            insert_idx = None
            continue
        if stripped.startswith("#"):
            insert_idx = i
            break
        insert_idx = None

    if insert_idx is None:
        insert_idx = len(lines)

    bullet_line = f"- {bullet_text}"
    lines.insert(insert_idx, bullet_line)
    return "\n".join(lines)


def _write_ledger(path: Path, metadata: dict[str, Any], body: str) -> None:
    metadata = _touch_updated_at(metadata)
    content = _format_frontmatter(metadata) + body + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class FactoryRunLedgerService:
    def __init__(self, base_dir: str | Path = "karkhana-runs") -> None:
        self.base_dir = Path(base_dir)

    def parse_text(self, text: str) -> dict[str, Any]:
        metadata, body = _parse_frontmatter(text)
        _validate_required(metadata)
        return {
            "metadata": metadata,
            "body": body,
            "run_id": metadata["run_id"],
            "title": metadata["title"],
            "status": metadata["status"],
            "stage": metadata["stage"],
            "created_at": metadata["created_at"],
            "updated_at": metadata["updated_at"],
        }

    def read_ledger(self, run_id: str) -> dict[str, Any]:
        path = self.base_dir / f"{run_id}.md"
        if not path.exists():
            raise FactoryRunLedgerError(f"Ledger not found: {run_id}")
        text = path.read_text(encoding="utf-8")
        return self.parse_text(text)

    def compact_context(self, ledger_path: str | Path, *, max_section_chars: int = 1200) -> dict[str, Any]:
        path = Path(ledger_path)
        if not path.is_absolute():
            path = self.base_dir / path
        parsed = self.parse_text(path.read_text(encoding="utf-8"))
        sections: dict[str, str] = {}
        for heading in COMPACT_CONTEXT_SECTIONS:
            text = _extract_section(parsed["body"], heading)
            sections[heading] = text[:max_section_chars].rstrip()
        return {
            "frontmatter": parsed["metadata"],
            "sections": sections,
            "truncated": any(len(_extract_section(parsed["body"], heading)) > max_section_chars for heading in COMPACT_CONTEXT_SECTIONS),
        }

    def create_ledger(
        self,
        run_id: str,
        title: str,
        *,
        status: str = "active",
        stage: str = "planning",
    ) -> Path:
        path = self.base_dir / f"{run_id}.md"
        if path.exists():
            raise FactoryRunLedgerError(f"Ledger already exists: {run_id}")
        now = _utcnow_iso()
        metadata: dict[str, Any] = {
            "run_id": run_id,
            "title": title,
            "status": status,
            "stage": stage,
            "created_at": now,
            "updated_at": now,
        }
        body = f"# {title}\n\n## Current goal\n\n\n"
        _write_ledger(path, metadata, body)
        return path

    def append_decision(
        self, run_id: str, *, date: str, decision: str, reason: str, made_by: str
    ) -> None:
        path = self.base_dir / f"{run_id}.md"
        text = path.read_text(encoding="utf-8")
        metadata, body = _parse_frontmatter(text)
        _validate_required(metadata)
        body = _append_table_row(body, "Decisions", [date, decision, reason, made_by])
        _write_ledger(path, metadata, body)

    def append_artifact(
        self, run_id: str, *, artifact_type: str, title: str, location: str, status: str
    ) -> None:
        path = self.base_dir / f"{run_id}.md"
        text = path.read_text(encoding="utf-8")
        metadata, body = _parse_frontmatter(text)
        _validate_required(metadata)
        body = _append_table_row(body, "Artifacts", [artifact_type, title, location, status])
        _write_ledger(path, metadata, body)

    def append_handoff(
        self,
        run_id: str,
        *,
        date: str,
        from_: str,
        to: str,
        summary: str,
        required_output: str,
    ) -> None:
        path = self.base_dir / f"{run_id}.md"
        text = path.read_text(encoding="utf-8")
        metadata, body = _parse_frontmatter(text)
        _validate_required(metadata)
        body = _append_table_row(body, "Handoffs", [date, from_, to, summary, required_output])
        _write_ledger(path, metadata, body)

    def append_codex_run(
        self,
        run_id: str,
        *,
        date: str,
        goal: str,
        branch: str,
        files_changed: str,
        verification: str,
        result: str,
    ) -> None:
        path = self.base_dir / f"{run_id}.md"
        text = path.read_text(encoding="utf-8")
        metadata, body = _parse_frontmatter(text)
        _validate_required(metadata)
        body = _append_table_row(body, "Codex runs", [date, goal, branch, files_changed, verification, result])
        _write_ledger(path, metadata, body)

    def append_risk(self, run_id: str, risk: str) -> None:
        path = self.base_dir / f"{run_id}.md"
        text = path.read_text(encoding="utf-8")
        metadata, body = _parse_frontmatter(text)
        _validate_required(metadata)
        body = _append_bullet(body, "Risks", risk)
        _write_ledger(path, metadata, body)

    def append_next_action(
        self, run_id: str, *, owner: str, action: str, priority: str
    ) -> None:
        path = self.base_dir / f"{run_id}.md"
        text = path.read_text(encoding="utf-8")
        metadata, body = _parse_frontmatter(text)
        _validate_required(metadata)
        body = _append_table_row(body, "Next actions", [owner, action, priority])
        _write_ledger(path, metadata, body)

    def append_reusable_lesson(self, run_id: str, lesson: str) -> None:
        path = self.base_dir / f"{run_id}.md"
        text = path.read_text(encoding="utf-8")
        metadata, body = _parse_frontmatter(text)
        _validate_required(metadata)
        body = _append_bullet(body, "Reusable lessons", lesson)
        _write_ledger(path, metadata, body)


# ---------------------------------------------------------------------------
# DynamoDB Ledger Entity
# ---------------------------------------------------------------------------

class DynamoDBLedgerService:
    """Stores ledger metadata in DynamoDB. Markdown body is stored in S3."""

    def __init__(
        self,
        table_name: str | None = None,
        region_name: str = "us-east-1",
    ) -> None:
        import boto3

        from backend.app.aws_endpoints import endpoint_url

        self.table_name = table_name or os.environ.get("DYNAMODB_TABLE_NAME", "IdeaRefinery")
        self.table = boto3.resource(
            "dynamodb",
            region_name=region_name,
            endpoint_url=endpoint_url("dynamodb"),
        ).Table(self.table_name)
        self._region = region_name

    def _ledger_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def _clean_item(self, item: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in item.items() if v is not None}

    def create_ledger_record(
        self,
        run_id: str,
        title: str,
        status: str = "active",
        stage: str = "planning",
        s3_key: str = "",
    ) -> str:
        ledger_id = self._ledger_id()
        now = _utcnow_iso()
        item = self._clean_item({
            "PK": f"LEDGER#{ledger_id}",
            "SK": "METADATA",
            "entity": "FactoryRunLedger",
            "ledger_id": ledger_id,
            "run_id": run_id,
            "GSI1PK": f"RUN#{run_id}",
            "GSI1SK": f"LEDGER#{now}#{ledger_id}",
            "title": title,
            "status": status,
            "stage": stage,
            "created_at": now,
            "updated_at": now,
            "s3_key": s3_key,
        })
        self.table.put_item(Item=item)
        return ledger_id

    def get_ledger_record(self, ledger_id: str) -> dict[str, Any]:
        response = self.table.get_item(Key={"PK": f"LEDGER#{ledger_id}", "SK": "METADATA"})
        item = response.get("Item")
        if not item:
            raise FactoryRunLedgerError(f"Ledger record not found: {ledger_id}")
        return dict(item)

    def list_ledgers_for_run(self, run_id: str) -> list[dict[str, Any]]:
        from boto3.dynamodb.conditions import Key

        items: list[dict[str, Any]] = []
        kwargs: dict[str, Any] = {
            "IndexName": "GSI1",
            "KeyConditionExpression": Key("GSI1PK").eq(f"RUN#{run_id}") & Key("GSI1SK").begins_with("LEDGER#"),
        }
        while True:
            response = self.table.query(**kwargs)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            kwargs["ExclusiveStartKey"] = last_key
        return items

    def update_ledger_record(self, ledger_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        record = self.get_ledger_record(ledger_id)
        allowed = {"title", "status", "stage", "s3_key"}
        update_expr_parts: list[str] = []
        expr_names: dict[str, str] = {}
        expr_values: dict[str, Any] = {}
        for key, value in updates.items():
            if key not in allowed:
                continue
            name_placeholder = f"#{key}"
            value_placeholder = f":{key}"
            update_expr_parts.append(f"{name_placeholder} = {value_placeholder}")
            expr_names[name_placeholder] = key
            expr_values[value_placeholder] = value

        if not update_expr_parts:
            return record

        update_expr_parts.append("#updated_at = :updated_at")
        expr_names["#updated_at"] = "updated_at"
        expr_values[":updated_at"] = _utcnow_iso()

        self.table.update_item(
            Key={"PK": f"LEDGER#{ledger_id}", "SK": "METADATA"},
            UpdateExpression="SET " + ", ".join(update_expr_parts),
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )
        return self.get_ledger_record(ledger_id)


# ---------------------------------------------------------------------------
# S3 Storage
# ---------------------------------------------------------------------------

_LEDGER_S3_BUCKET: str | None = None


def _get_ledger_s3_bucket() -> str:
    global _LEDGER_S3_BUCKET
    if _LEDGER_S3_BUCKET is None:
        _LEDGER_S3_BUCKET = os.environ.get(
            "IDEAREFINERY_S3_BUCKET", os.environ.get("S3_BUCKET", "idea-refinery-storage")
        )
    return _LEDGER_S3_BUCKET


def _get_s3_client():
    import boto3

    from backend.app.aws_endpoints import endpoint_url

    return boto3.client(
        "s3",
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        endpoint_url=endpoint_url("s3"),
    )


def store_ledger_body(ledger_id: str, run_id: str, body_text: str) -> str:
    """Upload ledger markdown body to S3. Returns the S3 key."""
    bucket = _get_ledger_s3_bucket()
    s3_key = f"ledgers/{run_id}/{ledger_id}.md"
    _get_s3_client().put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=body_text.encode("utf-8"),
        ContentType="text/markdown; charset=utf-8",
    )
    return s3_key


def get_ledger_body(ledger_id: str, run_id: str) -> str:
    """Download ledger markdown body from S3."""
    bucket = _get_ledger_s3_bucket()
    s3_key = f"ledgers/{run_id}/{ledger_id}.md"
    response = _get_s3_client().get_object(Bucket=bucket, Key=s3_key)
    return response["Body"].read().decode("utf-8")
