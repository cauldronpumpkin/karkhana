"""Tests for the Factory Run data model lifecycle."""
from __future__ import annotations

import pytest

from backend.app.repository import (
    FactoryBatch,
    FactoryPhase,
    FactoryRun,
    FactoryRunTrackingManifest,
    InMemoryRepository,
    TemplateArtifact,
    TemplateManifest,
    TemplateMemory,
    TemplatePack,
    TemplateUpdateProposal,
    VerificationRun,
    set_repository,
)


@pytest.fixture
def repo():
    r = InMemoryRepository()
    set_repository(r)
    return r


@pytest.mark.asyncio
async def test_template_pack_crud(repo):
    pack = TemplatePack(
        template_id="fullstack-saas-v1",
        version="1.0.0",
        channel="stable",
        display_name="Fullstack SaaS",
        description="Full-stack SaaS template",
    )
    saved = await repo.save_template_pack(pack)
    assert saved.template_id == "fullstack-saas-v1"
    assert saved.version == "1.0.0"

    fetched = await repo.get_template_pack("fullstack-saas-v1")
    assert fetched is not None
    assert fetched.display_name == "Fullstack SaaS"

    all_packs = await repo.list_template_packs()
    assert len(all_packs) == 1


@pytest.mark.asyncio
async def test_template_artifact_crud(repo):
    await repo.save_template_pack(TemplatePack(
        template_id="tpl-1",
        version="1.0.0",
        channel="stable",
        display_name="T",
        description="",
    ))
    artifact = TemplateArtifact(
        template_id="tpl-1",
        artifact_key="prompts/setup.md",
        content_type="text/markdown",
        uri="s3://bucket/artifacts/tpl-1/setup.md",
        content="# Setup",
    )
    saved = await repo.save_template_artifact(artifact)
    assert saved.artifact_key == "prompts/setup.md"

    fetched = await repo.get_template_artifact("tpl-1", "prompts/setup.md")
    assert fetched is not None
    assert fetched.uri.startswith("s3://")

    artifacts = await repo.list_template_artifacts("tpl-1")
    assert len(artifacts) == 1


@pytest.mark.asyncio
async def test_template_manifest_crud(repo):
    manifest = TemplateManifest(
        template_id="tpl-1",
        version="1.0.0",
        artifact_keys=["prompts/setup.md", "configs/docker.yml"],
        metadata_={"generated_by": "test"},
    )
    saved = await repo.save_template_manifest(manifest)
    assert saved.version == "1.0.0"

    fetched = await repo.get_template_manifest("tpl-1", "1.0.0")
    assert fetched is not None
    assert len(fetched.artifact_keys) == 2

    manifests = await repo.list_template_manifests("tpl-1")
    assert len(manifests) == 1


@pytest.mark.asyncio
async def test_template_memory_crud(repo):
    mem = TemplateMemory(
        template_id="tpl-1",
        key="preferred_stack",
        value="react-fastapi",
        category="learned",
    )
    saved = await repo.upsert_template_memory(mem)
    assert saved.value == "react-fastapi"

    fetched = await repo.get_template_memory("tpl-1", "preferred_stack")
    assert fetched is not None

    updated = TemplateMemory(
        template_id="tpl-1",
        key="preferred_stack",
        value="nextjs-fastapi",
        category="learned",
    )
    await repo.upsert_template_memory(updated)
    fetched2 = await repo.get_template_memory("tpl-1", "preferred_stack")
    assert fetched2 is not None
    assert fetched2.value == "nextjs-fastapi"

    all_mem = await repo.list_template_memories("tpl-1")
    assert len(all_mem) == 1

    deleted = await repo.delete_template_memory("tpl-1", "preferred_stack")
    assert deleted is True
    assert await repo.get_template_memory("tpl-1", "preferred_stack") is None
    assert await repo.delete_template_memory("tpl-1", "nonexistent") is False


@pytest.mark.asyncio
async def test_template_update_proposal_crud(repo):
    proposal = TemplateUpdateProposal(
        template_id="tpl-1",
        proposed_by="worker-1",
        change_type="phase_add",
        description="Add integration testing phase",
        payload_uri="s3://bucket/proposals/1.json",
    )
    saved = await repo.save_template_update_proposal(proposal)
    assert saved.status == "pending"

    fetched = await repo.get_template_update_proposal("tpl-1", saved.id)
    assert fetched is not None
    assert fetched.change_type == "phase_add"

    all_proposals = await repo.list_template_update_proposals("tpl-1")
    assert len(all_proposals) == 1

    pending = await repo.list_template_update_proposals("tpl-1", status="pending")
    assert len(pending) == 1
    approved = await repo.list_template_update_proposals("tpl-1", status="approved")
    assert len(approved) == 0

    fetched.status = "approved"
    await repo.save_template_update_proposal(fetched)
    refreshed = await repo.get_template_update_proposal("tpl-1", saved.id)
    assert refreshed is not None
    assert refreshed.status == "approved"


@pytest.mark.asyncio
async def test_factory_run_lifecycle(repo):
    run = FactoryRun(
        idea_id="idea-001",
        template_id="fullstack-saas-v1",
        status="queued",
        config={"stack": "react"},
    )
    created = await repo.create_factory_run(run)
    assert created.status == "queued"
    assert created.id

    fetched = await repo.get_factory_run(created.id)
    assert fetched is not None
    assert fetched.template_id == "fullstack-saas-v1"

    fetched.status = "running"
    await repo.save_factory_run(fetched)
    refreshed = await repo.get_factory_run(created.id)
    assert refreshed is not None
    assert refreshed.status == "running"


@pytest.mark.asyncio
async def test_factory_run_tracking_manifest_crud(repo):
    run = await repo.create_factory_run(FactoryRun(idea_id="idea-001", template_id="fullstack-saas-v1"))
    manifest = FactoryRunTrackingManifest(
        factory_run_id=run.id,
        idea_id=run.idea_id,
        template_id=run.template_id,
        template_version="2.0.0",
        run_config={"stack": "python-fastapi"},
        phase_summary=[{"phase_key": "scaffold", "status": "running"}],
        batch_summary=[{"batch_key": "scaffold-batch-1", "status": "queued"}],
        verification_state={"status": "pending"},
    )

    saved = await repo.save_factory_run_tracking_manifest(manifest)
    assert saved.factory_run_id == run.id
    assert saved.template_version == "2.0.0"

    fetched = await repo.get_factory_run_tracking_manifest(run.id)
    assert fetched is not None
    assert fetched.run_config["stack"] == "python-fastapi"
    assert fetched.phase_summary[0]["phase_key"] == "scaffold"


@pytest.mark.asyncio
async def test_factory_run_list_by_idea(repo):
    await repo.create_factory_run(FactoryRun(idea_id="idea-A", template_id="t1"))
    await repo.create_factory_run(FactoryRun(idea_id="idea-A", template_id="t2"))
    await repo.create_factory_run(FactoryRun(idea_id="idea-B", template_id="t1"))

    by_idea_a = await repo.list_factory_runs(idea_id="idea-A")
    assert len(by_idea_a) == 2

    by_template = await repo.list_factory_runs(template_id="t1")
    assert len(by_template) == 2

    all_runs = await repo.list_factory_runs()
    assert len(all_runs) == 3


@pytest.mark.asyncio
async def test_factory_run_filter_by_status(repo):
    r1 = await repo.create_factory_run(FactoryRun(idea_id="i1", template_id="t1", status="queued"))
    r2 = await repo.create_factory_run(FactoryRun(idea_id="i2", template_id="t1", status="running"))
    r3 = await repo.create_factory_run(FactoryRun(idea_id="i3", template_id="t1", status="completed"))

    active = await repo.list_factory_runs(statuses={"queued", "running"})
    assert len(active) == 2
    ids = {r.id for r in active}
    assert r1.id in ids
    assert r2.id in ids
    assert r3.id not in ids


@pytest.mark.asyncio
async def test_factory_phase_lifecycle(repo):
    run = await repo.create_factory_run(FactoryRun(idea_id="idea-001", template_id="t1"))

    phase1 = await repo.save_factory_phase(FactoryPhase(
        factory_run_id=run.id,
        phase_key="project_setup",
        phase_order=1,
        status="running",
    ))
    phase2 = await repo.save_factory_phase(FactoryPhase(
        factory_run_id=run.id,
        phase_key="backend",
        phase_order=2,
        status="pending",
    ))

    phases = await repo.list_factory_phases(run.id)
    assert len(phases) == 2
    assert phases[0].phase_key == "project_setup"
    assert phases[1].phase_key == "backend"

    fetched = await repo.get_factory_phase(run.id, phase1.id)
    assert fetched is not None
    assert fetched.phase_order == 1

    none_phase = await repo.get_factory_phase("nonexistent-run", phase1.id)
    assert none_phase is None

    phase1.status = "completed"
    await repo.save_factory_phase(phase1)
    updated = await repo.get_factory_phase(run.id, phase1.id)
    assert updated is not None
    assert updated.status == "completed"


@pytest.mark.asyncio
async def test_factory_batch_lifecycle(repo):
    run = await repo.create_factory_run(FactoryRun(idea_id="idea-001", template_id="t1"))
    phase = await repo.save_factory_phase(FactoryPhase(
        factory_run_id=run.id,
        phase_key="backend",
        phase_order=1,
    ))

    batch = await repo.save_factory_batch(FactoryBatch(
        factory_phase_id=phase.id,
        factory_run_id=run.id,
        batch_key="backend-api",
        input_uri="s3://bucket/input/api.json",
    ))
    assert batch.status == "pending"

    fetched = await repo.get_factory_batch(batch.id)
    assert fetched is not None
    assert fetched.batch_key == "backend-api"
    assert fetched.input_uri is not None

    batches = await repo.list_factory_batches(phase.id)
    assert len(batches) == 1

    batch.status = "running"
    batch.worker_id = "worker-001"
    await repo.save_factory_batch(batch)
    updated = await repo.get_factory_batch(batch.id)
    assert updated is not None
    assert updated.status == "running"
    assert updated.worker_id == "worker-001"


@pytest.mark.asyncio
async def test_verification_run_lifecycle(repo):
    run = await repo.create_factory_run(FactoryRun(idea_id="idea-001", template_id="t1"))
    phase = await repo.save_factory_phase(FactoryPhase(
        factory_run_id=run.id,
        phase_key="testing",
        phase_order=1,
    ))
    batch = await repo.save_factory_batch(FactoryBatch(
        factory_phase_id=phase.id,
        factory_run_id=run.id,
        batch_key="integration-tests",
    ))

    vr = await repo.save_verification_run(VerificationRun(
        factory_batch_id=batch.id,
        factory_run_id=run.id,
        verification_type="test",
        result_uri="s3://bucket/results/test-output.xml",
        result_summary="42 passed, 0 failed",
    ))
    assert vr.status == "pending"

    fetched = await repo.get_verification_run(vr.id)
    assert fetched is not None
    assert fetched.verification_type == "test"

    runs = await repo.list_verification_runs(batch.id)
    assert len(runs) == 1
    assert runs[0].result_summary == "42 passed, 0 failed"

    vr.status = "passed"
    await repo.save_verification_run(vr)
    updated = await repo.get_verification_run(vr.id)
    assert updated is not None
    assert updated.status == "passed"


@pytest.mark.asyncio
async def test_full_factory_run_journey(repo):
    pack = await repo.save_template_pack(TemplatePack(
        template_id="fullstack-saas-v1",
        version="1.0.0",
        channel="stable",
        display_name="Fullstack SaaS",
        description="",
    ))
    await repo.save_template_artifact(TemplateArtifact(
        template_id=pack.template_id,
        artifact_key="prompts/setup.md",
        content_type="text/markdown",
        uri="s3://bucket/prompts/setup.md",
    ))

    run = await repo.create_factory_run(FactoryRun(
        idea_id="idea-journey",
        template_id=pack.template_id,
        config={"stack": "nextjs"},
    ))
    assert run.status == "queued"

    phase_setup = await repo.save_factory_phase(FactoryPhase(
        factory_run_id=run.id, phase_key="project_setup", phase_order=1, status="running",
    ))
    batch_init = await repo.save_factory_batch(FactoryBatch(
        factory_phase_id=phase_setup.id,
        factory_run_id=run.id,
        batch_key="scaffold",
        worker_id="worker-001",
        status="running",
    ))

    batch_init.status = "completed"
    batch_init.output_uri = "s3://bucket/output/scaffold.zip"
    await repo.save_factory_batch(batch_init)

    vr = await repo.save_verification_run(VerificationRun(
        factory_batch_id=batch_init.id,
        factory_run_id=run.id,
        verification_type="lint",
    ))
    vr.status = "passed"
    vr.result_summary = "0 errors, 0 warnings"
    await repo.save_verification_run(vr)

    phase_setup.status = "completed"
    await repo.save_factory_phase(phase_setup)

    run.status = "completed"
    run.tracking_manifest_uri = "s3://bucket/manifests/run-001.json"
    from backend.app.repository import utcnow
    run.completed_at = utcnow()
    await repo.save_factory_run(run)

    final_run = await repo.get_factory_run(run.id)
    assert final_run is not None
    assert final_run.status == "completed"
    assert final_run.tracking_manifest_uri is not None
    assert final_run.completed_at is not None

    phases = await repo.list_factory_phases(run.id)
    assert len(phases) == 1
    assert phases[0].status == "completed"

    batches = await repo.list_factory_batches(phase_setup.id)
    assert len(batches) == 1
    assert batches[0].status == "completed"

    verifications = await repo.list_verification_runs(batch_init.id)
    assert len(verifications) == 1
    assert verifications[0].status == "passed"
