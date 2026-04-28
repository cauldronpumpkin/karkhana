"""AGENTS.md as a versioned Template Artifact.

AGENTS.md is extracted from the project root and stored as a TemplateArtifact
so that Factory Runs and template packs can reference it by URI/version instead
of copying one-off prompt text everywhere.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from backend.app.repository import TemplateArtifact, get_repository
from backend.app.services.project_twin import to_jsonable


DEFAULT_AGENTS_MD_PATH = Path("AGENTS.md")
DEFAULT_ARTIFACT_KEY = "AGENTS.md"
DEFAULT_CONTENT_TYPE = "text/markdown"


class AgentsMdArtifactService:
    """Manage AGENTS.md as a versioned Template Artifact.

    Responsibilities:
    - Import AGENTS.md from disk into the artifact store.
    - Retrieve a specific version or the latest version.
    - List versions for a template pack.
    - Provide a URI reference for inclusion in worker contracts.
    """

    def __init__(self, repo: Any | None = None) -> None:
        self._repo = repo or get_repository()

    @staticmethod
    def _versioned_key(version: str) -> str:
        return f"{DEFAULT_ARTIFACT_KEY}#{version}"

    async def import_from_disk(
        self,
        template_id: str,
        version: str = "1.0.0",
        path: Path | None = None,
        compatibility: dict[str, Any] | None = None,
    ) -> TemplateArtifact:
        """Read AGENTS.md from disk and store it as a TemplateArtifact."""
        read_path = path or DEFAULT_AGENTS_MD_PATH
        content = read_path.read_text(encoding="utf-8") if read_path.exists() else ""
        uri = f"template://{template_id}/{DEFAULT_ARTIFACT_KEY}?v={version}"
        artifact = TemplateArtifact(
            template_id=template_id,
            artifact_key=self._versioned_key(version),
            content_type=DEFAULT_CONTENT_TYPE,
            uri=uri,
            content=content,
            version=version,
            compatibility=compatibility or {"min_template_pack": "1.0.0"},
            metadata_={
                "source": str(read_path),
                "imported_at": os.path.getmtime(read_path) if read_path.exists() else None,
            },
        )
        await self._repo.save_template_artifact(artifact)
        # Return a copy with the logical artifact key for callers
        return self._normalize_key(artifact)

    def _normalize_key(self, artifact: TemplateArtifact) -> TemplateArtifact:
        """Return a copy with the canonical artifact key."""
        from dataclasses import replace
        return replace(artifact, artifact_key=DEFAULT_ARTIFACT_KEY)

    async def get_artifact(
        self,
        template_id: str,
        version: str | None = None,
    ) -> TemplateArtifact | None:
        """Get the AGENTS.md artifact for a template.

        If version is None, returns the latest version by created_at.
        """
        all_artifacts = await self._repo.list_template_artifacts(template_id)
        agents_artifacts = [
            a for a in all_artifacts
            if a.artifact_key.startswith(f"{DEFAULT_ARTIFACT_KEY}#")
        ]
        if not agents_artifacts:
            return None
        if version:
            key = self._versioned_key(version)
            found = next((a for a in agents_artifacts if a.artifact_key == key), None)
            return self._normalize_key(found) if found else None
        return self._normalize_key(max(agents_artifacts, key=lambda a: a.created_at))

    async def list_versions(self, template_id: str) -> list[dict[str, Any]]:
        """List all stored AGENTS.md versions for a template pack."""
        all_artifacts = await self._repo.list_template_artifacts(template_id)
        agents_artifacts = sorted(
            [a for a in all_artifacts if a.artifact_key.startswith(f"{DEFAULT_ARTIFACT_KEY}#")],
            key=lambda a: a.created_at,
            reverse=True,
        )
        return [
            {
                "version": a.version,
                "uri": a.uri,
                "content_type": a.content_type,
                "compatibility": a.compatibility,
                "created_at": to_jsonable(a.created_at),
            }
            for a in agents_artifacts
        ]

    async def get_reference_for_contract(
        self,
        template_id: str,
        version: str | None = None,
    ) -> dict[str, Any] | None:
        """Return a lightweight reference dict for inclusion in worker contracts."""
        artifact = await self.get_artifact(template_id, version)
        if not artifact:
            return None
        return {
            "key": artifact.artifact_key,
            "uri": artifact.uri,
            "version": artifact.version,
            "content_type": artifact.content_type,
            "compatibility": artifact.compatibility,
        }
