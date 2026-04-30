from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from backend.app.services.llm import LLMService


class FactoryRole(str, Enum):
    PLANNER = "planner"
    ARCHITECT = "architect"
    BATCH_PLANNER = "batch_planner"
    WORKER = "worker"
    VERIFIER = "verifier"
    BUG_FIXER = "bug_fixer"
    INTEGRATOR = "integrator"
    RELEASE_MANAGER = "release_manager"
    TEMPLATE_CURATOR = "template_curator"


@dataclass(frozen=True)
class RoleDefinition:
    name: str
    purpose: str
    prompt_template: str
    required_inputs: tuple[str, ...]
    output_schema: dict[str, Any]


def _schema(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "required": required,
        "properties": properties,
        "additionalProperties": True,
    }


ROLE_DEFINITIONS: dict[FactoryRole, RoleDefinition] = {
    FactoryRole.PLANNER: RoleDefinition(
        name="Planner",
        purpose="Convert project context into a concise factory execution plan.",
        prompt_template="""Role: Planner
Goal: Convert the project twin, template pack, current factory run config, and available code/research context into a concise factory execution plan.
Inputs:
- project: {project}
- template: {template}
- factory_run_id: {factory_run_id}
- run_config: {run_config}
- code_context: {code_context}
- research_context: {research_context}
Output must match schema: {output_schema}
Do not write implementation code. Produce a plan that downstream batch planners and workers can execute.""",
        required_inputs=("project", "template", "factory_run_id", "run_config", "code_context", "research_context"),
        output_schema=_schema(
            {
                "factory_goal": {"type": "string"},
                "phases": {"type": "array", "items": {"type": "object"}},
                "risks": {"type": "array", "items": {"type": "string"}},
                "assumptions": {"type": "array", "items": {"type": "string"}},
            },
            ["factory_goal", "phases", "risks", "assumptions"],
        ),
    ),
    FactoryRole.ARCHITECT: RoleDefinition(
        name="Architect",
        purpose="Turn planning context into an implementation architecture and service boundary proposal.",
        prompt_template="""Role: Architect
Goal: Review the project, template, and factory run context and design the implementation architecture, service boundaries, and integration points.
Inputs:
- project: {project}
- template: {template}
- factory_run_id: {factory_run_id}
- run_config: {run_config}
- architecture_context: {architecture_context}
Output must match schema: {output_schema}
Do not write implementation code. Focus on architecture, boundaries, and risks.""",
        required_inputs=("project", "template", "factory_run_id", "run_config", "architecture_context"),
        output_schema=_schema(
            {
                "architecture_summary": {"type": "string"},
                "service_boundaries": {"type": "array", "items": {"type": "object"}},
                "risks": {"type": "array", "items": {"type": "string"}},
                "assumptions": {"type": "array", "items": {"type": "string"}},
            },
            ["architecture_summary", "service_boundaries", "risks", "assumptions"],
        ),
    ),
    FactoryRole.BATCH_PLANNER: RoleDefinition(
        name="Batch Planner",
        purpose="Split the factory plan into phase-aligned execution batches.",
        prompt_template="""Role: Batch Planner
Goal: Convert the factory plan into an execution batch plan for the current phase or phase set.
Inputs:
- project: {project}
- template: {template}
- factory_run_id: {factory_run_id}
- run_config: {run_config}
- phase_blueprints: {phase_blueprints}
- code_context: {code_context}
- research_context: {research_context}
Output must match schema: {output_schema}
Keep the plan aligned with template phases and ready for worker execution.""",
        required_inputs=("project", "template", "factory_run_id", "run_config", "phase_blueprints", "code_context", "research_context"),
        output_schema=_schema(
            {
                "batch_goal": {"type": "string"},
                "batches": {"type": "array", "items": {"type": "object"}},
                "dependencies": {"type": "array", "items": {"type": "string"}},
                "risks": {"type": "array", "items": {"type": "string"}},
                "assumptions": {"type": "array", "items": {"type": "string"}},
            },
            ["batch_goal", "batches", "dependencies", "risks", "assumptions"],
        ),
    ),
    FactoryRole.WORKER: RoleDefinition(
        name="Worker",
        purpose="Execute a factory phase on the assigned branch and report implementation results.",
        prompt_template="""Role: Worker
Goal: Execute factory phase '{phase_key}' for {project_repo_full_name} on branch {branch_name}.
Before editing:
- Read graphify-out/GRAPH_REPORT.md for god nodes and community structure.
- Read graphify-out/wiki/index.md if it exists for codebase navigation.
Deliverables:
- Implement the phase goal: {goal}
- Run verification commands: {verification_commands}
- Run graphify update . after code changes.
Context:
- project: {project}
- template: {template}
- phase: {phase}
- batch: {batch}
- context_files: {context_files}
- constraints: {constraints}
- quality_gates: {quality_gates}
- deliverables: {deliverables}
- graphify_instructions: {graphify_instructions}
Factory Run Ledger:
- Context: {ledger_context}
- Before implementation, use ledger context for continuity, preserve recorded decisions, continue from current_next_action, and avoid repeating resolved debates.
- For read_only ledgers, use context but do not update the ledger.
- For required or strict ledgers, update it before completion after meaningful implementation work.
- Prefer these sections: ## Codex runs, ## Repo changes, ## Verification, ## Risks, ## Next actions, ## Reusable lessons.
- Do not invent verification results, commit SHAs, or follow-up work. Use pending/not run when unknown.
- Report ledger_updated and ledger_sections_updated in the final output.
Output must match schema: {output_schema}""",
        required_inputs=(
            "project",
            "template",
            "factory_run_id",
            "phase",
            "batch",
            "branch_name",
            "phase_key",
            "project_repo_full_name",
            "context_files",
            "constraints",
            "quality_gates",
            "deliverables",
            "verification_commands",
            "graphify_instructions",
            "ledger_context",
            "goal",
        ),
        output_schema=_schema(
            {
                "summary": {"type": "string"},
                "files_modified": {"type": "array", "items": {"type": "string"}},
                "tests_passed": {"type": "boolean"},
                "test_output": {"type": "string"},
                "graphify_updated": {"type": "boolean"},
                "ledger_updated": {"type": "boolean"},
                "ledger_sections_updated": {"type": "array", "items": {"type": "string"}},
                "commit_sha": {"type": "string"},
                "branch_name": {"type": "string"},
                "phase_artifacts": {"type": "object"},
            },
            ["summary", "files_modified", "tests_passed", "test_output", "graphify_updated", "branch_name", "phase_artifacts"],
        ),
    ),
    FactoryRole.VERIFIER: RoleDefinition(
        name="Verifier",
        purpose="Describe the verification contract for a completed worker result.",
        prompt_template="""Role: Verifier
Goal: Verify the worker result for factory batch {factory_batch_id} in run {factory_run_id}.
Inputs:
- project: {project}
- factory_run_id: {factory_run_id}
- factory_batch_id: {factory_batch_id}
- verification_commands: {verification_commands}
- expected_result_fields: {expected_result_fields}
Output must match schema: {output_schema}
This contract is embedded in the worker payload in v1; do not queue a separate verifier task.""",
        required_inputs=("project", "factory_run_id", "factory_batch_id", "verification_commands", "expected_result_fields"),
        output_schema=_schema(
            {
                "tests_passed": {"type": "boolean"},
                "test_output": {"type": "string"},
                "failure_classification": {"type": "string"},
                "summary": {"type": "string"},
                "graphify_updated": {"type": "boolean"},
                "changed_files": {"type": "array", "items": {"type": "string"}},
            },
            ["tests_passed", "test_output", "failure_classification", "summary", "graphify_updated", "changed_files"],
        ),
    ),
    FactoryRole.BUG_FIXER: RoleDefinition(
        name="Bug Fixer",
        purpose="Repair a failed factory batch with the smallest safe change.",
        prompt_template="""Role: Bug Fixer
Goal: Repair failed factory batch {batch_key} for run {factory_run_id}.
Failure classification: {failure_classification}
Failing output: {command_output}
Guardrails:
- Make the smallest safe fix.
- Do not delete or skip tests.
- Do not refactor unrelated code.
Before editing:
- Read graphify-out/GRAPH_REPORT.md for god nodes and community structure.
- Read graphify-out/wiki/index.md if it exists for codebase navigation.
Acceptance criteria:
{acceptance_criteria}
Graphify instructions: {graphify_instructions}
Run graphify update . after code changes.
Output must match schema: {output_schema}""",
        required_inputs=(
            "project",
            "factory_run_id",
            "batch",
            "batch_key",
            "failure_classification",
            "command_output",
            "recent_diff",
            "changed_files",
            "acceptance_criteria",
            "attempt_number",
            "graphify_instructions",
        ),
        output_schema=_schema(
            {
                "summary": {"type": "string"},
                "root_cause": {"type": "string"},
                "files_modified": {"type": "array", "items": {"type": "string"}},
                "tests_passed": {"type": "boolean"},
                "test_output": {"type": "string"},
                "repair_attempted": {"type": "boolean"},
                "graphify_updated": {"type": "boolean"},
            },
            ["summary", "root_cause", "files_modified", "tests_passed", "test_output", "repair_attempted", "graphify_updated"],
        ),
    ),
    FactoryRole.INTEGRATOR: RoleDefinition(
        name="Integrator",
        purpose="Integrate completed work across batches and reconcile remaining gaps.",
        prompt_template="""Role: Integrator
Goal: Merge completed batch work into a coherent integrated result for run {factory_run_id}.
Inputs:
- project: {project}
- factory_run_id: {factory_run_id}
- integration_scope: {integration_scope}
- verification_summary: {verification_summary}
Output must match schema: {output_schema}""",
        required_inputs=("project", "factory_run_id", "integration_scope", "verification_summary"),
        output_schema=_schema(
            {
                "summary": {"type": "string"},
                "files_modified": {"type": "array", "items": {"type": "string"}},
                "tests_passed": {"type": "boolean"},
                "test_output": {"type": "string"},
                "integration_notes": {"type": "array", "items": {"type": "string"}},
                "graphify_updated": {"type": "boolean"},
            },
            ["summary", "files_modified", "tests_passed", "test_output", "integration_notes", "graphify_updated"],
        ),
    ),
    FactoryRole.RELEASE_MANAGER: RoleDefinition(
        name="Release Manager",
        purpose="Package a factory run into a release-ready delivery summary.",
        prompt_template="""Role: Release Manager
Goal: Prepare the release handoff for run {factory_run_id}.
Inputs:
- project: {project}
- factory_run_id: {factory_run_id}
- release_scope: {release_scope}
- verification_summary: {verification_summary}
Output must match schema: {output_schema}""",
        required_inputs=("project", "factory_run_id", "release_scope", "verification_summary"),
        output_schema=_schema(
            {
                "summary": {"type": "string"},
                "release_notes": {"type": "array", "items": {"type": "string"}},
                "checks_completed": {"type": "array", "items": {"type": "string"}},
                "risks": {"type": "array", "items": {"type": "string"}},
                "graphify_updated": {"type": "boolean"},
            },
            ["summary", "release_notes", "checks_completed", "risks", "graphify_updated"],
        ),
    ),
    FactoryRole.TEMPLATE_CURATOR: RoleDefinition(
        name="Template Curator",
        purpose="Translate factory learnings into template updates.",
        prompt_template="""Role: Template Curator
Goal: Turn the factory run learnings into candidate template updates.
Inputs:
- template: {template}
- template_artifacts: {template_artifacts}
- factory_run_learnings: {factory_run_learnings}
Output must match schema: {output_schema}""",
        required_inputs=("template", "template_artifacts", "factory_run_learnings"),
        output_schema=_schema(
            {
                "summary": {"type": "string"},
                "changes_proposed": {"type": "array", "items": {"type": "object"}},
                "rationale": {"type": "array", "items": {"type": "string"}},
                "files_modified": {"type": "array", "items": {"type": "string"}},
                "tests_passed": {"type": "boolean"},
                "graphify_updated": {"type": "boolean"},
            },
            ["summary", "changes_proposed", "rationale", "files_modified", "tests_passed", "graphify_updated"],
        ),
    ),
}


class RolePromptBuilder:
    @classmethod
    def definition(cls, role: FactoryRole | str) -> RoleDefinition:
        role_key = role if isinstance(role, FactoryRole) else FactoryRole(str(role).strip().lower())
        return ROLE_DEFINITIONS[role_key]

    @classmethod
    def build(
        cls,
        role: FactoryRole | str,
        context: dict[str, Any],
        provider: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        definition = cls.definition(role)
        cls._validate_context(definition, context)
        provider_info = cls._resolve_provider(provider, model)
        rendered_context = {key: cls._render_value(value) for key, value in context.items()}
        rendered_context["output_schema"] = json.dumps(definition.output_schema, indent=2, sort_keys=True)
        prompt = definition.prompt_template.format(**rendered_context)
        messages = [
            {
                "role": "system",
                "content": f"You are the {definition.name} role for Karkhana factory runs. Follow the contract exactly.",
            },
            {"role": "user", "content": prompt},
        ]
        return {
            "role": definition.name.lower().replace(" ", "_"),
            "role_name": definition.name,
            "purpose": definition.purpose,
            "provider": provider_info["provider"],
            "model": provider_info["model"],
            "messages": messages,
            "prompt": prompt,
            "prompt_template": definition.prompt_template,
            "required_inputs": list(definition.required_inputs),
            "output_schema": definition.output_schema,
        }

    @staticmethod
    def _resolve_provider(provider: str | None, model: str | None) -> dict[str, str]:
        service = LLMService()
        provider_info = service.get_provider(provider)
        if model:
            provider_info["model"] = model
        return provider_info

    @staticmethod
    def _validate_context(definition: RoleDefinition, context: dict[str, Any]) -> None:
        missing = []
        for key in definition.required_inputs:
            if key not in context or RolePromptBuilder._is_missing(context[key]):
                missing.append(key)
        if missing:
            raise ValueError(f"Missing required inputs for role {definition.name}: {', '.join(missing)}")

    @staticmethod
    def _is_missing(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        return False

    @staticmethod
    def _render_value(value: Any) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value, indent=2, sort_keys=True, default=str)
