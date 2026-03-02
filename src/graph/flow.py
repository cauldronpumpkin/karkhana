"""LangGraph state machine definition with dashboard + command-center event integration."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

from langgraph.graph import END, StateGraph

from src.agents.architect_agent import ArchitectAgent
from src.agents.critic_agent import CriticAgent
from src.agents.coder_agent import CoderAgent
from src.agents.pm_agent import PMAgent
from src.agents.pm_consensus import PMConsensusAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.taskmaster import Taskmaster
from src.command_center.service import CommandCenterService
from src.config import config
from src.graph.agent_comms import (
    build_agent_decision,
    is_duplicate_request,
    normalize_request,
    request_fingerprint,
    route_request_targets,
)
from src.sandbox.executor import SandboxExecutor
from src.sandbox.language_adapters import adapter_for_file
from src.command_center.models import ReasoningConfig
from src.types.state import WorkingState
from src.utils.start_scripts import generate_start_script

STAGE_ORDER = [
    "pm_agent",
    "pm_consensus",
    "architect_agent",
    "agent_coordinator",
    "agent_resolution",
    "agent_escalation",
    "taskmaster",
    "coder_agent",
    "reviewer_agent",
    "sandbox_executor",
]


def _progress_for_stage(stage: str | None) -> float:
    if not stage:
        return 0.0
    try:
        idx = STAGE_ORDER.index(stage)
    except ValueError:
        return 0.0
    return round((idx / max(len(STAGE_ORDER), 1)) * 100, 1)


def _agent_comms_enabled(state: WorkingState) -> bool:
    return bool(getattr(state, "agent_comms_enabled", False) or config.agent_comms.enabled)


def _effective_reasoning(state: WorkingState) -> ReasoningConfig:
    raw = state.reasoning_config or {}
    if not isinstance(raw, dict):
        raw = {}
    if not raw:
        raw = config.reasoning.model_dump()
    return ReasoningConfig.model_validate(raw)


async def _emit_thinking(state: WorkingState, source: str, thinking: str) -> None:
    if not thinking:
        return
    reasoning = _effective_reasoning(state)
    if reasoning.thinking_visibility == "off":
        return
    payload = {"source": source, "thinking": thinking[:12000]}
    if reasoning.thinking_visibility == "logs":
        await _log(state, "info", source, "Thinking trace captured", payload)
    await _emit("reasoning_thinking", payload, state)


def _iteration_budget_seconds(split_percent: int, total_seconds: int) -> float:
    split = max(0, min(100, int(split_percent)))
    base = max(10.0, float(total_seconds))
    return max(5.0, base * (split / 100.0))


def _clean_relative(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _run_command_supported(adapter) -> bool:
    return bool(adapter is not None and adapter.available())


def _next_stage_from_origin(state: WorkingState) -> str:
    origin = str(state.coordination_origin or "")
    if origin == "after_architect":
        return "taskmaster"
    if origin == "before_coder":
        return "coder_agent"
    if origin == "after_reviewer":
        if _agent_comms_enabled(state):
            return "coder_agent" if not bool(getattr(state, "review_passed", False)) else "sandbox_executor"
        return "coder_agent" if not bool(getattr(state, "review_passed", False)) else "sandbox_executor"
    return "taskmaster"


def _rejected_dependencies(state: WorkingState) -> list[str]:
    rejected: list[str] = []
    for message in state.resolved_agent_requests or []:
        if str(message.get("message_type")) != "dependency_approval_request":
            continue
        content = message.get("content_json") or {}
        if not isinstance(content, dict):
            continue
        decision = content.get("decision") or {}
        if str(decision.get("status", "")).lower() != "rejected":
            continue
        dependency = content.get("dependency_name") or content.get("dependency") or message.get("topic")
        if dependency:
            rejected.append(str(dependency))
    return rejected


async def _emit(event_type: str, payload: dict | None = None, state: WorkingState | None = None):
    """Emit an event to the dashboard/event bus."""
    try:
        from src.dashboard.event_bus import EventBus

        out = payload.copy() if payload else {}
        if state and state.job_id and "job_id" not in out:
            out["job_id"] = state.job_id
        bus = EventBus.get()
        await bus.emit(event_type, out)
        if state and state.job_id:
            from src.llm.context_manager import ContextManager

            await ContextManager.get().observe_event(state.job_id, event_type, out)
        if event_type == "stage_start" and state and state.job_id:
            await bus.emit(
                "job_progress",
                {
                    "job_id": state.job_id,
                    "stage": out.get("stage"),
                    "progress_percent": _progress_for_stage(out.get("stage")),
                },
            )
    except Exception:
        pass


async def _log(state: WorkingState, level: str, source: str, message: str, meta: dict | None = None):
    """Emit a normalized job log event."""
    await _emit(
        "job_log",
        {
            "level": level,
            "source": source,
            "message": message,
            "meta": meta or {},
        },
        state,
    )


async def _wait_approval(stage: str, data: dict, state: WorkingState) -> dict:
    """Block until the user approves in dashboard mode."""
    try:
        from src.dashboard.event_bus import EventBus

        await _emit("job_decision_required", {"stage": stage, "decision_type": "approval", "data": data}, state)
        return await EventBus.get().wait_for_approval(stage, data, job_id=state.job_id)
    except Exception:
        return data


async def pm_agent_node(state: WorkingState) -> dict:
    """Run PM agent to generate PRD."""
    await _emit("stage_start", {"stage": "pm_agent"}, state)
    await _log(state, "info", "pm_agent", "Generating PRD")

    agent = PMAgent()
    agent.set_runtime_context(job_id=state.job_id, stage="pm_agent", context_type="user_intent")
    prd = await agent.generate_prd(state.raw_idea)

    await _emit("stage_output", {"stage": "pm_agent", "output": prd}, state)

    if state.dashboard_mode and state.approval_required:
        prd = await _wait_approval("pm_agent", prd, state)

    await _emit("stage_complete", {"stage": "pm_agent"}, state)
    return {
        "prd_drafts": [prd],
    }


async def pm_consensus_node(state: WorkingState) -> dict:
    """Run PM Consensus agent to merge PRD drafts."""
    await _emit("stage_start", {"stage": "pm_consensus"}, state)

    drafts = getattr(state, "prd_drafts", [])
    if not drafts:
        drafts = [state.prd] if state.prd else []

    if not drafts:
        final_prd: dict = {"title": "Untitled", "problem_statement": state.raw_idea, "core_features": []}
    else:
        agent = PMConsensusAgent()
        agent.set_runtime_context(job_id=state.job_id, stage="pm_consensus", context_type="timeline_event")
        final_prd = await agent.merge_prds(drafts) if len(drafts) > 1 else drafts[0]

    await _emit("stage_output", {"stage": "pm_consensus", "output": final_prd}, state)

    if state.dashboard_mode and state.approval_required:
        final_prd = await _wait_approval("pm_consensus", final_prd, state)

    await _emit("stage_complete", {"stage": "pm_consensus"}, state)

    return {
        "prd": final_prd,
        "llm_calls_count": state.llm_calls_count + 1,
    }


async def architect_agent_node(state: WorkingState) -> dict:
    """Run Architect agent to define tech stack and file tree."""
    await _emit("stage_start", {"stage": "architect_agent"}, state)

    if not state.prd:
        raise ValueError("PRD must be generated before architecture")

    reasoning = _effective_reasoning(state)
    agent = ArchitectAgent()
    agent.set_runtime_context(job_id=state.job_id, stage="architect_agent", context_type="timeline_event")
    async def _single_candidate(idx: int) -> dict:
        try:
            return await agent.generate_architecture(
                state.prd,
                candidate_id=idx,
                thinking_modules_enabled=reasoning.thinking_modules_enabled,
            )
        except TypeError:
            # Backward compatibility for tests/patches using old method signature.
            return await agent.generate_architecture(state.prd)

    if reasoning.enabled:
        candidates = await agent.generate_architecture_candidates(
            state.prd,
            count=reasoning.architect_tot_paths,
            parallel=reasoning.architect_tot_parallel,
            thinking_modules_enabled=reasoning.thinking_modules_enabled,
        )
    else:
        candidates = [await _single_candidate(1)]

    for idx, candidate in enumerate(candidates):
        await _emit(
            "architect_candidate_generated",
            {
                "stage": "architect_agent",
                "candidate_index": idx,
                "candidate_meta": candidate.get("candidate_meta", {}),
            },
            state,
        )
        await _emit_thinking(state, f"architect_candidate_{idx}", str(candidate.get("thinking", "")))

    critic_report: dict[str, object] = {"winner_index": 0, "winner_score": 0, "debate": []}
    winner_index = 0
    if reasoning.enabled and reasoning.critic_enabled and len(candidates) > 1:
        try:
            critic = CriticAgent()
            critic.set_runtime_context(job_id=state.job_id, stage="architect_agent", context_type="timeline_event")
            critic_report = await critic.debate_architecture_candidates(
                prd=state.prd,
                candidates=candidates,
                thinking_modules_enabled=reasoning.thinking_modules_enabled,
            )
            winner_index = int(critic_report.get("winner_index", 0) or 0)
            winner_index = max(0, min(winner_index, len(candidates) - 1))
            await _emit(
                "critic_debate_completed",
                {
                    "stage": "architect_agent",
                    "winner_index": winner_index,
                    "winner_score": critic_report.get("winner_score", 0),
                    "report": critic_report,
                },
                state,
            )
            await _emit_thinking(state, "critic_agent", str(critic_report.get("thinking", "")))
        except Exception as exc:
            await _log(state, "warn", "critic_agent", f"Critic failed, defaulting to first candidate: {exc}")
            critic_report = {"winner_index": 0, "winner_score": 0, "debate": [], "error": str(exc)}
            winner_index = 0

    architecture = candidates[winner_index] if candidates else {}
    await _emit("stage_output", {"stage": "architect_agent", "output": architecture}, state)

    if state.dashboard_mode and state.approval_required:
        architecture = await _wait_approval("architect_agent", architecture, state)

    comm_requests: list[dict] = []
    if _agent_comms_enabled(state):
        comm_requests = agent.generate_coordination_requests(prd=state.prd or {}, architecture=architecture)

    await _emit("stage_complete", {"stage": "architect_agent"}, state)

    file_tree = architecture.get("file_tree", {})
    pending = []
    for directory, files in file_tree.items():
        pending.extend([f"{directory.rstrip('/')}/{name}" for name in files])

    return {
        "tech_stack": architecture,
        "architecture_candidates": candidates,
        "critic_report": critic_report,
        "file_tree": file_tree,
        "pending_files": pending,
        "agent_outbox": comm_requests,
        "coordination_origin": "after_architect",
        "reasoning_metrics": {
            **(state.reasoning_metrics or {}),
            "architect_candidates_generated": len(candidates),
            "critic_winner_index": winner_index,
            "critic_winner_score": critic_report.get("winner_score", 0),
        },
        "llm_calls_count": state.llm_calls_count + 1,
    }


async def taskmaster_node(state: WorkingState) -> dict:
    """Queue next file for implementation."""
    await _emit("stage_start", {"stage": "taskmaster"}, state)

    if not state.file_tree:
        await _emit("stage_complete", {"stage": "taskmaster", "output": {"queued": 0, "total": 0}}, state)
        return {"status": "no_files", "pending_files": [], "current_file": None, "agent_outbox": []}

    all_files: list[str] = []
    for directory, files in state.file_tree.items():
        for file in files:
            full_path = f"{directory.rstrip('/')}/{file}"
            all_files.append(full_path)

    pending = [f for f in all_files if f not in (state.completed_files or set())]

    if not pending and all_files:
        try:
            generate_start_script("nextjs_fastapi", ".")
            await _log(state, "info", "taskmaster", "Generated start scripts")
        except Exception as exc:
            await _log(state, "warn", "taskmaster", f"Failed to generate start scripts: {exc}")

    comm_requests: list[dict] = []
    if _agent_comms_enabled(state):
        comm_requests = Taskmaster().generate_coordination_requests(
            all_files=all_files,
            pending_files=pending,
            completed_files=state.completed_files or set(),
        )

    await _emit(
        "stage_complete",
        {
            "stage": "taskmaster",
            "output": {"queued": len(pending), "total": len(all_files)},
        },
        state,
    )

    return {
        "pending_files": pending,
        "current_file": pending[0] if pending else None,
        "status": "files_queued",
        "agent_outbox": comm_requests,
        "coordination_origin": "before_coder" if pending else None,
    }


def _materialize_workspace(tmpdir: str, files: dict[str, str]) -> None:
    for rel_path, content in files.items():
        safe = _clean_relative(rel_path)
        full = os.path.join(tmpdir, safe)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as handle:
            handle.write(content or "")


async def _run_tdd_iteration(
    *,
    state: WorkingState,
    adapter,
    workspace_files: dict[str, str],
    test_file_path: str,
    impl_file_path: str,
) -> tuple[bool, str, str]:
    executor = SandboxExecutor()
    with tempfile.TemporaryDirectory() as tmpdir:
        _materialize_workspace(tmpdir, workspace_files)
        cwd = Path(tmpdir)
        test_cmd = adapter.generate_test_command(file_path=_clean_relative(impl_file_path), test_file_path=_clean_relative(test_file_path))
        returncode, stdout, stderr = await executor.execute(test_cmd, cwd)
        if returncode == 0:
            return True, stdout or "", stderr or ""

        syntax_cmd = adapter.generate_syntax_command(file_path=_clean_relative(impl_file_path))
        syn_code, syn_out, syn_err = await executor.execute(syntax_cmd, cwd)
        syntax_ok = syn_code == 0
        joined_stderr = (stderr or "") + ("\n" + syn_err if syn_err else "")
        joined_stdout = (stdout or "") + ("\n" + syn_out if syn_out else "")
        return syntax_ok, joined_stdout, joined_stderr


async def coder_agent_node(state: WorkingState) -> dict:
    """Coder writes implementation for current file."""
    await _emit("stage_start", {"stage": "coder_agent", "file": state.current_file}, state)

    if not state.current_file or not state.file_tree:
        await _log(state, "warn", "coder_agent", "No file to write")
        return {"error": "No file to write"}

    reasoning = _effective_reasoning(state)
    existing_files = dict(state.generated_files_map or {})
    agent = CoderAgent()
    agent.set_runtime_context(job_id=state.job_id, stage="coder_agent", context_type="coding_artifact")

    requirements = []
    if state.prd and isinstance(state.prd, dict):
        core_features = state.prd.get("core_features", [])
        requirements = [f.get("description", "") for f in core_features[:3] if isinstance(f, dict)]

    rejected_dependencies = _rejected_dependencies(state)
    if rejected_dependencies:
        requirements.extend([f"Do not use dependency: {dep}" for dep in rejected_dependencies])

    if _agent_comms_enabled(state):
        comm_requests = agent.generate_coordination_requests(
            file_path=state.current_file,
            requirements=requirements,
            prd_context=state.prd or {},
            resolved_requests=state.resolved_agent_requests or [],
        )
        if comm_requests:
            await _log(
                state,
                "info",
                "coder_agent",
                "Coder emitted coordination request(s) before writing code.",
                {"count": len(comm_requests), "file": state.current_file},
            )
            await _emit("stage_complete", {"stage": "coder_agent", "file": state.current_file}, state)
            return {
                "agent_outbox": comm_requests,
                "coordination_origin": "before_coder",
            }

    try:
        adapter = adapter_for_file(state.current_file)
        tdd_requested = bool(reasoning.enabled and reasoning.tdd_enabled)
        tdd_enabled = bool(tdd_requested and _run_command_supported(adapter))
        if tdd_requested and not tdd_enabled:
            await _log(
                state,
                "warn",
                "coder_agent",
                "TDD requested but language adapter/toolchain unavailable; falling back to direct generation.",
                {"file": state.current_file},
            )
        tdd_stats: dict[str, object] = {"enabled": tdd_enabled, "iterations": 0, "passed": True}
        code = ""
        test_file_path = ""
        tests_code = ""
        iteration_start = time.monotonic()
        budget_seconds = _iteration_budget_seconds(reasoning.tdd_time_split_percent, config.sandbox.timeout)

        if tdd_enabled:
            test_file_path = agent.test_file_for(state.current_file)
            test_result = await agent.write_tests(
                file_path=state.current_file,
                prd_context=state.prd or {},
                tech_stack=state.tech_stack or {},
                requirements=requirements,
                existing_files=existing_files,
                thinking_modules_enabled=reasoning.thinking_modules_enabled,
            )
            tests_code = test_result["code"]
            await _emit(
                "tdd_test_generated",
                {
                    "stage": "coder_agent",
                    "file": state.current_file,
                    "test_file_path": test_file_path,
                    "code": tests_code,
                },
                state,
            )
            await _emit_thinking(state, "coder_tests", test_result.get("thinking", ""))
            impl_result = await agent.write_impl_from_tests(
                file_path=state.current_file,
                test_file_path=test_file_path,
                test_code=tests_code,
                prd_context=state.prd or {},
                requirements=requirements,
                existing_files={**existing_files, test_file_path: tests_code},
                thinking_modules_enabled=reasoning.thinking_modules_enabled,
            )
            code = impl_result["code"]
            await _emit_thinking(state, "coder_impl", impl_result.get("thinking", ""))

            for iteration in range(1, reasoning.tdd_max_iterations + 1):
                await _emit(
                    "tdd_iteration_started",
                    {"stage": "coder_agent", "file": state.current_file, "iteration": iteration},
                    state,
                )
                tdd_stats["iterations"] = iteration
                workspace = {**existing_files, state.current_file: code, test_file_path: tests_code}
                passed, stdout, stderr = await _run_tdd_iteration(
                    state=state,
                    adapter=adapter,
                    workspace_files=workspace,
                    test_file_path=test_file_path,
                    impl_file_path=state.current_file,
                )
                if passed:
                    await _emit(
                        "tdd_iteration_passed",
                        {"stage": "coder_agent", "file": state.current_file, "iteration": iteration},
                        state,
                    )
                    tdd_stats["passed"] = True
                    break

                await _emit(
                    "tdd_iteration_failed",
                    {
                        "stage": "coder_agent",
                        "file": state.current_file,
                        "iteration": iteration,
                        "stderr": (stderr or "")[:2000],
                    },
                    state,
                )
                tdd_stats["passed"] = False
                if (time.monotonic() - iteration_start) >= budget_seconds:
                    await _emit(
                        "tdd_budget_exhausted",
                        {
                            "stage": "coder_agent",
                            "file": state.current_file,
                            "iteration": iteration,
                            "budget_seconds": round(budget_seconds, 2),
                        },
                        state,
                    )
                    if not reasoning.tdd_fail_open:
                        raise RuntimeError("TDD budget exhausted before passing tests.")
                    break

                repair = await agent.repair_from_test_failure(
                    file_path=state.current_file,
                    test_file_path=test_file_path,
                    test_code=tests_code,
                    stderr=stderr or stdout,
                    current_code=code,
                    iteration_context=f"iteration={iteration}, budget_seconds={budget_seconds}",
                    thinking_modules_enabled=reasoning.thinking_modules_enabled,
                )
                code = repair["code"]
                await _emit_thinking(state, "coder_repair", repair.get("thinking", ""))
        else:
            try:
                file_result = await agent.write_file(
                    file_path=state.current_file,
                    prd_context=state.prd or {},
                    tech_stack=state.tech_stack or {},
                    requirements=requirements,
                    existing_files=existing_files,
                    thinking_modules_enabled=reasoning.thinking_modules_enabled,
                )
            except TypeError:
                # Backward compatibility for legacy monkeypatched signatures in tests.
                file_result = await agent.write_file(
                    file_path=state.current_file,
                    prd_context=state.prd or {},
                    tech_stack=state.tech_stack or {},
                    requirements=requirements,
                    existing_files=existing_files,
                )

            if isinstance(file_result, dict):
                code = str(file_result.get("code", ""))
                await _emit_thinking(state, "coder_file", str(file_result.get("thinking", "")))
            else:
                code = str(file_result)

        generated_map = dict(existing_files)
        generated_map[state.current_file] = code
        if tests_code:
            generated_map[test_file_path] = tests_code

        await _emit(
            "code_generated",
            {
                "stage": "coder_agent",
                "file_path": state.current_file,
                "code": code,
            },
            state,
        )
        await _emit("stage_complete", {"stage": "coder_agent", "file": state.current_file}, state)

        return {
            "current_code": code,
            "generated_files_map": generated_map,
            "tdd_loop_stats": {**(state.tdd_loop_stats or {}), state.current_file: tdd_stats},
            "reasoning_metrics": {
                **(state.reasoning_metrics or {}),
                "tdd_iterations_total": int((state.reasoning_metrics or {}).get("tdd_iterations_total", 0))
                + int(tdd_stats.get("iterations", 0)),
            },
            "agent_outbox": [],
            "coordination_origin": None,
            "llm_calls_count": state.llm_calls_count + 1,
        }
    except Exception as exc:
        await _emit(
            "error",
            {
                "stage": "coder_agent",
                "message": str(exc),
                "file": state.current_file,
            },
            state,
        )
        return {"error": str(exc), "agent_outbox": []}


async def reviewer_agent_node(state: WorkingState) -> dict:
    """Reviewer validates code quality."""
    await _emit("stage_start", {"stage": "reviewer_agent", "file": state.current_file}, state)

    if not state.current_code or not state.current_file:
        await _emit("stage_complete", {"stage": "reviewer_agent"}, state)
        return {"review_passed": True, "review_issues": [], "agent_outbox": []}

    agent = ReviewerAgent()
    agent.set_runtime_context(job_id=state.job_id, stage="reviewer_agent", context_type="review")

    project_context = {
        "title": state.prd.get("title", "Generic Project") if isinstance(state.prd, dict) else str(state.prd),
        "problem_statement": state.prd.get("problem_statement", "") if isinstance(state.prd, dict) else "",
    }

    review_result = await agent.review_code(
        file_path=state.current_file,
        code_content=state.current_code,
        project_context=project_context,
    )

    passed = review_result.get("passed", False)
    comm_requests: list[dict] = []
    if _agent_comms_enabled(state):
        comm_requests = agent.generate_coordination_requests(
            file_path=state.current_file,
            review_result=review_result,
        )

    await _emit(
        "review_result",
        {
            "stage": "reviewer_agent",
            "passed": passed,
            "issues": review_result.get("issues", []),
            "file": state.current_file,
        },
        state,
    )
    await _emit("stage_complete", {"stage": "reviewer_agent"}, state)

    return {
        "review_passed": passed,
        "review_issues": review_result.get("issues", []),
        "agent_outbox": comm_requests,
        "coordination_origin": "after_reviewer" if comm_requests else None,
        "llm_calls_count": state.llm_calls_count + 1,
    }


async def sandbox_executor_node(state: WorkingState) -> dict:
    """Run tests and lint checks in sandbox."""
    await _emit("stage_start", {"stage": "sandbox_executor", "file": state.current_file}, state)

    if not state.current_code or not state.current_file:
        await _emit("stage_complete", {"stage": "sandbox_executor"}, state)
        return {"sandbox_passed": True}

    executor = SandboxExecutor()
    adapter = adapter_for_file(state.current_file)
    generated_files = dict(state.generated_files_map or {})
    generated_files[state.current_file] = state.current_code

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            _materialize_workspace(tmpdir, generated_files)
            if adapter and adapter.available():
                returncode, stdout, stderr = await executor.execute(
                    adapter.generate_syntax_command(file_path=_clean_relative(state.current_file)),
                    Path(tmpdir),
                )
            else:
                returncode, stdout, stderr = await executor.execute(
                    ["python", "-m", "py_compile", _clean_relative(state.current_file)],
                    Path(tmpdir),
                )

            sandbox_passed = returncode == 0

            await _emit(
                "sandbox_result",
                {
                    "stage": "sandbox_executor",
                    "passed": sandbox_passed,
                    "stdout": stdout[:500] if stdout else "",
                    "stderr": stderr[:500] if stderr else "",
                    "file": state.current_file,
                },
                state,
            )
            await _emit("stage_complete", {"stage": "sandbox_executor"}, state)

            return {
                "sandbox_passed": sandbox_passed,
                "completed_files": (state.completed_files | {state.current_file}) if sandbox_passed else state.completed_files,
                "llm_calls_count": state.llm_calls_count + 1,
            }
    except Exception as exc:
        await _emit(
            "error",
            {
                "stage": "sandbox_executor",
                "message": str(exc),
                "file": state.current_file,
            },
            state,
        )
        return {"error": str(exc), "sandbox_passed": False}


async def agent_coordinator_node(state: WorkingState) -> dict:
    """Persist and route outbound inter-agent requests with dedupe + budget controls."""
    await _emit(
        "stage_start",
        {
            "stage": "agent_coordinator",
            "origin": state.coordination_origin,
            "round": state.coordination_rounds + 1,
        },
        state,
    )

    if not _agent_comms_enabled(state):
        await _emit("stage_complete", {"stage": "agent_coordinator", "disabled": True}, state)
        return {"coordination_action": "continue", "agent_outbox": []}

    pending = list(state.pending_agent_requests or [])
    resolved = list(state.resolved_agent_requests or [])
    outbox = list(state.agent_outbox or [])

    if not outbox and not pending:
        await _emit("stage_complete", {"stage": "agent_coordinator", "created": 0}, state)
        return {"coordination_action": "continue", "agent_outbox": []}

    budget = int(state.coordination_budget)
    round_number = int(state.coordination_rounds) + 1
    if budget <= 0:
        await _log(state, "warn", "agent_coordinator", "Coordination budget exhausted before request routing.")
        await _emit("stage_complete", {"stage": "agent_coordinator", "created": 0, "budget": 0}, state)
        return {
            "coordination_action": "escalate",
            "agent_outbox": [],
            "coordination_rounds": round_number,
            "coordination_budget": 0,
            "agent_blocked_reason": "Coordination budget exhausted before resolving pending requests.",
        }

    service = CommandCenterService.get()
    created_count = 0
    for raw_request in outbox:
        normalized = normalize_request(raw_request, default_from_agent=str(raw_request.get("from_agent") or "unknown_agent"))
        targets = route_request_targets(
            normalized["message_type"],
            normalized["topic"],
            normalized["content_json"],
        )
        for target in targets:
            request = {
                **normalized,
                "to_agent": target,
            }
            dedupe_key = request_fingerprint(request)
            request["dedupe_key"] = dedupe_key
            if is_duplicate_request(request, pending_requests=pending, resolved_requests=resolved):
                continue

            content_payload = dict(request["content_json"])
            content_payload["dedupe_key"] = dedupe_key
            persisted = await service.create_agent_message(
                job_id=state.job_id or "unknown",
                from_agent=request["from_agent"],
                to_agent=target,
                message_type=request["message_type"],
                topic=request["topic"],
                content=content_payload,
                blocking=bool(request["blocking"]),
                round_number=round_number,
            )
            if not persisted:
                continue
            persisted["dedupe_key"] = dedupe_key
            pending.append(persisted)
            created_count += 1

    await _emit(
        "stage_complete",
        {
            "stage": "agent_coordinator",
            "created": created_count,
            "pending": len(pending),
            "round": round_number,
        },
        state,
    )
    return {
        "pending_agent_requests": pending,
        "agent_outbox": [],
        "coordination_rounds": round_number,
        "coordination_budget": max(0, budget - 1),
        "coordination_action": "resolve",
    }


async def agent_resolution_node(state: WorkingState) -> dict:
    """Resolve pending inter-agent requests using routed target handlers."""
    await _emit("stage_start", {"stage": "agent_resolution", "round": state.coordination_rounds}, state)

    if not _agent_comms_enabled(state):
        await _emit("stage_complete", {"stage": "agent_resolution", "disabled": True}, state)
        return {"coordination_action": "continue"}

    pending = list(state.pending_agent_requests or [])
    if not pending:
        await _emit("stage_complete", {"stage": "agent_resolution", "resolved": 0}, state)
        return {"coordination_action": "continue"}

    resolved = list(state.resolved_agent_requests or [])
    still_pending: list[dict] = []
    unresolved_blocking = False
    unresolved_nonblocking = 0
    round_number = max(1, int(state.coordination_rounds))
    service = CommandCenterService.get()

    for message in pending:
        decision = build_agent_decision(
            message,
            state_context={
                "prd": state.prd,
                "tech_stack": state.tech_stack,
                "file_tree": state.file_tree,
            },
        )
        if decision is None:
            is_blocking = bool(message.get("blocking", False))
            if is_blocking:
                unresolved_blocking = True
                still_pending.append(message)
            else:
                unresolved_nonblocking += 1
                await _log(
                    state,
                    "warn",
                    "agent_resolution",
                    "Non-blocking agent request unresolved; continuing.",
                    {"message_id": message.get("id"), "topic": message.get("topic")},
                )
                auto_decision = {
                    "status": "needs_more_info",
                    "rationale": "Non-blocking request unresolved; continued execution.",
                    "metadata": {"auto_resolved": True},
                }
                resolved_message = await service.resolve_agent_message(
                    job_id=state.job_id or "unknown",
                    message_id=int(message.get("id", 0)),
                    decision=auto_decision,
                    round_number=round_number,
                )
                if resolved_message:
                    resolved_message["dedupe_key"] = message.get("dedupe_key")
                    resolved.append(resolved_message)
            continue

        resolved_message = await service.resolve_agent_message(
            job_id=state.job_id or "unknown",
            message_id=int(message.get("id", 0)),
            decision=decision,
            round_number=round_number,
        )
        if resolved_message:
            resolved_message["dedupe_key"] = message.get("dedupe_key")
            resolved.append(resolved_message)

    action = "continue"
    blocked_reason = None
    if unresolved_blocking:
        if int(state.coordination_budget) > 0:
            action = "retry"
        else:
            action = "escalate"
            blocked_reason = "Blocking unresolved requests with exhausted coordination budget."

    await _emit(
        "stage_complete",
        {
            "stage": "agent_resolution",
            "resolved": len(resolved),
            "pending": len(still_pending),
            "action": action,
        },
        state,
    )

    return {
        "pending_agent_requests": still_pending,
        "resolved_agent_requests": resolved,
        "coordination_action": action,
        "agent_blocked_reason": blocked_reason,
    }


async def agent_escalation_node(state: WorkingState) -> dict:
    """Escalate unresolved requests based on policy controls."""
    await _emit("stage_start", {"stage": "agent_escalation", "round": state.coordination_rounds}, state)

    if not _agent_comms_enabled(state):
        await _emit("stage_complete", {"stage": "agent_escalation", "disabled": True}, state)
        return {"coordination_action": "continue"}

    pending = list(state.pending_agent_requests or [])
    if not pending:
        await _emit("stage_complete", {"stage": "agent_escalation", "escalated": 0}, state)
        return {"coordination_action": "continue"}

    resolved = list(state.resolved_agent_requests or [])
    escalate_blocking_only = bool(getattr(state, "agent_comms_escalate_blocking_only", True))
    reason = state.agent_blocked_reason or "Escalated unresolved agent request."
    round_number = max(1, int(state.coordination_rounds))
    service = CommandCenterService.get()

    remaining: list[dict] = []
    escalated_count = 0
    for message in pending:
        is_blocking = bool(message.get("blocking", False))
        if escalate_blocking_only and not is_blocking:
            remaining.append(message)
            continue

        escalated = await service.escalate_agent_message(
            job_id=state.job_id or "unknown",
            message_id=int(message.get("id", 0)),
            reason=reason,
            round_number=round_number,
        )
        if escalated:
            escalated["dedupe_key"] = message.get("dedupe_key")
            resolved.append(escalated)
            escalated_count += 1
        else:
            remaining.append(message)

    await _log(
        state,
        "warn",
        "agent_escalation",
        f"Escalated {escalated_count} unresolved agent request(s).",
        {"round": round_number, "reason": reason},
    )
    await _emit(
        "stage_complete",
        {
            "stage": "agent_escalation",
            "escalated": escalated_count,
            "remaining": len(remaining),
        },
        state,
    )
    return {
        "pending_agent_requests": remaining,
        "resolved_agent_requests": resolved,
        "coordination_action": "continue",
    }


def route_after_architect(state: WorkingState) -> str:
    return "coordinate" if _agent_comms_enabled(state) else "taskmaster"


def route_after_taskmaster(state: WorkingState) -> str:
    if not state.pending_files:
        return "final_review"
    return "coordinate" if _agent_comms_enabled(state) else "coder_agent"


def route_after_coder(state: WorkingState) -> str:
    if _agent_comms_enabled(state) and state.agent_outbox:
        return "coordinate"
    return "reviewer_agent"


def should_retry_coder(state: WorkingState) -> str:
    """Determine if coder should retry or move to sandbox."""
    if _agent_comms_enabled(state):
        if state.current_file and not bool(getattr(state, "review_passed", False)):
            return "retry_coder"
        return "review"
    if state.current_file and not bool(getattr(state, "review_passed", False)):
        return "retry_coder"
    return "review"


def route_after_reviewer(state: WorkingState) -> str:
    if _agent_comms_enabled(state) and state.agent_outbox:
        return "coordinate"
    return should_retry_coder(state)


def route_after_resolution(state: WorkingState) -> str:
    action = str(state.coordination_action or "continue")
    if action == "retry":
        return "retry_coordination"
    if action == "escalate":
        return "escalate"
    return _next_stage_from_origin(state)


def route_after_escalation(state: WorkingState) -> str:
    return _next_stage_from_origin(state)


def route_to_sandbox(state: WorkingState) -> str:
    """Route to taskmaster or end based on pending files."""
    if state.pending_files:
        return "execute_sandbox"
    return "final_review"


workflow = StateGraph(WorkingState)

workflow.add_node("pm_agent_1", pm_agent_node)
workflow.add_node("pm_agent_2", pm_agent_node)
workflow.add_node("pm_consensus", pm_consensus_node)
workflow.add_node("architect_agent", architect_agent_node)
workflow.add_node("agent_coordinator", agent_coordinator_node)
workflow.add_node("agent_resolution", agent_resolution_node)
workflow.add_node("agent_escalation", agent_escalation_node)
workflow.add_node("taskmaster", taskmaster_node)
workflow.add_node("coder_agent", coder_agent_node)
workflow.add_node("reviewer_agent", reviewer_agent_node)
workflow.add_node("sandbox_executor", sandbox_executor_node)


def start_parallel_pms(state: WorkingState) -> dict:
    _ = state
    return {}


workflow.add_node("start", start_parallel_pms)
workflow.set_entry_point("start")
workflow.add_edge("start", "pm_agent_1")
workflow.add_edge("start", "pm_agent_2")

workflow.add_edge("pm_agent_1", "pm_consensus")
workflow.add_edge("pm_agent_2", "pm_consensus")
workflow.add_edge("pm_consensus", "architect_agent")
workflow.add_conditional_edges(
    "architect_agent",
    route_after_architect,
    {
        "coordinate": "agent_coordinator",
        "taskmaster": "taskmaster",
    },
)

workflow.add_conditional_edges(
    "taskmaster",
    route_after_taskmaster,
    {
        "coordinate": "agent_coordinator",
        "coder_agent": "coder_agent",
        "final_review": END,
    },
)

workflow.add_conditional_edges(
    "coder_agent",
    route_after_coder,
    {
        "coordinate": "agent_coordinator",
        "reviewer_agent": "reviewer_agent",
    },
)

workflow.add_conditional_edges(
    "reviewer_agent",
    route_after_reviewer,
    {
        "coordinate": "agent_coordinator",
        "retry_coder": "coder_agent",
        "review": "sandbox_executor",
    },
)

workflow.add_edge("agent_coordinator", "agent_resolution")
workflow.add_conditional_edges(
    "agent_resolution",
    route_after_resolution,
    {
        "retry_coordination": "agent_coordinator",
        "escalate": "agent_escalation",
        "taskmaster": "taskmaster",
        "coder_agent": "coder_agent",
        "sandbox_executor": "sandbox_executor",
    },
)
workflow.add_conditional_edges(
    "agent_escalation",
    route_after_escalation,
    {
        "taskmaster": "taskmaster",
        "coder_agent": "coder_agent",
        "sandbox_executor": "sandbox_executor",
    },
)

workflow.add_conditional_edges(
    "sandbox_executor",
    route_to_sandbox,
    {
        "execute_sandbox": "taskmaster",
        "final_review": END,
    },
)

app = workflow.compile()
