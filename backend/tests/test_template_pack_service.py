import pytest

from backend.app.repository import InMemoryRepository, TemplateArtifact, TemplateManifest, TemplatePack, set_repository
from backend.app.services.template_pack import BUILTIN_TEMPLATE_ID, MEMORY_KEY, TemplatePackService


async def _seed_broken_template(repo: InMemoryRepository) -> None:
    await repo.save_template_pack(
        TemplatePack(
            template_id="broken-template",
            version="1.0.0",
            channel="stable",
            display_name="Broken Template",
            description="Template with an intentionally invalid manifest",
        )
    )
    await repo.save_template_manifest(
        TemplateManifest(
            template_id="broken-template",
            version="1.0.0",
            artifact_keys=[],
            metadata_={
                "id": "broken-template",
                "name": "",
                "version": "1.0.0",
                "schema_version": "v0",
                "description": "",
                "stack": {},
                "required_tools": [],
                "artifacts": [],
                "allowed_paths": [],
                "forbidden_paths": [],
                "verification_commands": [],
                "graphify_expectations": {},
                "guardrails": [],
                "review_metadata": {},
            },
        )
    )


@pytest.mark.asyncio
async def test_template_pack_service_seeds_builtin_pack_and_exposes_manifest() -> None:
    repo = InMemoryRepository()
    set_repository(repo)
    service = TemplatePackService(repo=repo)

    packs = await service.list_template_packs()

    assert len(packs) == 1
    pack = packs[0]
    assert pack["template_id"] == BUILTIN_TEMPLATE_ID
    assert pack["manifest"]["schema_version"] == "v0"
    assert pack["required_tools"] == ["node", "pnpm", "supabase", "stripe"]
    assert "AGENTS.md" in [ref["key"] for ref in pack["artifact_refs"]]
    assert MEMORY_KEY in [ref["key"] for ref in pack["artifact_refs"]]


@pytest.mark.asyncio
async def test_template_pack_service_resolves_agents_hierarchy_in_order() -> None:
    repo = InMemoryRepository()
    set_repository(repo)
    service = TemplatePackService(repo=repo)

    resolved = await service.resolve_agents_hierarchy(BUILTIN_TEMPLATE_ID, target_path="frontend/src/routes")

    assert [item["key"] for item in resolved][:2] == ["AGENTS.md", "AGENTS.override.md"]
    assert resolved[0]["scope_path"] == "."
    assert resolved[1]["scope_path"] == "frontend"


@pytest.mark.asyncio
async def test_template_pack_service_validate_template_reports_guardrails_and_memory() -> None:
    repo = InMemoryRepository()
    set_repository(repo)
    service = TemplatePackService(repo=repo)
    await service.ensure_seeded()

    await repo.save_template_artifact(
        TemplateArtifact(
            template_id=BUILTIN_TEMPLATE_ID,
            artifact_key=MEMORY_KEY,
            content_type="text/markdown",
            uri=f"template://{BUILTIN_TEMPLATE_ID}/{MEMORY_KEY}",
            content="user: please do this\nassistant: sure\nsystem: transcript",
            version="0.0.1",
            metadata_={"kind": "memory"},
        )
    )

    result = await service.validate_template(
        BUILTIN_TEMPLATE_ID,
        changed_files=[".karkhana/generated.ts", "backend/tests/verification/harness.ts"],
        verification_commands=["pnpm test"],
        graphify_updated=False,
        completed=True,
    )

    assert result["valid"] is False
    codes = {issue["code"] for issue in result["issues"]}
    assert "memory_transcript" in codes
    assert "path_forbidden" in codes or "normal_run_forbidden_path" in codes
    assert "missing_graphify_command" in codes
    assert result["guardrail_state"] == "fail"
    assert result["graphify_state"] == "fail"


@pytest.mark.asyncio
async def test_template_pack_service_validate_template_reports_missing_fields() -> None:
    repo = InMemoryRepository()
    set_repository(repo)
    await _seed_broken_template(repo)
    service = TemplatePackService(repo=repo)

    result = await service.validate_template("broken-template")

    assert result["valid"] is False
    codes = {issue["code"] for issue in result["issues"]}
    assert "missing_name" in codes
    assert "missing_required_tools" in codes
    assert "missing_artifacts" in codes
