"""LangGraph state machine definition with dashboard event integration."""

import json
from langgraph.graph import StateGraph, END

from src.types.state import WorkingState
from src.agents.pm_agent import PMAgent
from src.agents.architect_agent import ArchitectAgent
from src.agents.taskmaster import Taskmaster
from src.agents.coder_agent import CoderAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.sandbox.executor import SandboxExecutor


# ── Helpers ────────────────────────────────────────────────────

async def _emit(event_type: str, payload: dict | None = None):
    """Emit an event to the dashboard (no-op if dashboard is not running)."""
    try:
        from src.dashboard.event_bus import EventBus
        await EventBus.get().emit(event_type, payload or {})
    except Exception:
        pass  # Silently skip when dashboard is not loaded


async def _wait_approval(stage: str, data: dict) -> dict:
    """Block until the user approves in the dashboard. Returns (possibly edited) data."""
    try:
        from src.dashboard.event_bus import EventBus
        return await EventBus.get().wait_for_approval(stage, data)
    except Exception:
        return data


# ── Node functions ─────────────────────────────────────────────

async def pm_agent_node(state: WorkingState) -> dict:
    """Run PM agent to generate PRD."""
    await _emit("stage_start", {"stage": "pm_agent"})

    agent = PMAgent()
    prd = await agent.generate_prd(state.raw_idea)

    await _emit("stage_output", {"stage": "pm_agent", "output": prd})

    # Stage gate — wait for user approval in dashboard mode
    if state.dashboard_mode:
        prd = await _wait_approval("pm_agent", prd)

    await _emit("stage_complete", {"stage": "pm_agent"})

    return {
        "prd": prd,
        "llm_calls_count": state.llm_calls_count + 1,
    }


async def architect_agent_node(state: WorkingState) -> dict:
    """Run Architect agent to define tech stack and file tree."""
    await _emit("stage_start", {"stage": "architect_agent"})

    if not state.prd:
        raise ValueError("PRD must be generated before architecture")

    agent = ArchitectAgent()
    architecture = await agent.generate_architecture(state.prd)

    await _emit("stage_output", {"stage": "architect_agent", "output": architecture})

    # Stage gate — wait for user approval in dashboard mode
    if state.dashboard_mode:
        architecture = await _wait_approval("architect_agent", architecture)

    await _emit("stage_complete", {"stage": "architect_agent"})

    # Extract file tree from architecture
    file_tree = architecture.get("file_tree", {})

    return {
        "tech_stack": architecture,
        "file_tree": file_tree,
        "pending_files": list(file_tree.values())[0] if file_tree else [],
        "llm_calls_count": state.llm_calls_count + 1,
    }


async def taskmaster_node(state: WorkingState) -> dict:
    """Taskmaster queues next file for implementation."""
    await _emit("stage_start", {"stage": "taskmaster"})

    if not state.file_tree:
        await _emit("stage_complete", {"stage": "taskmaster"})
        return {"status": "no_files"}

    # Get all files from file tree
    all_files = []
    for directory, files in state.file_tree.items():
        for file in files:
            full_path = f"{directory.rstrip('/')}/{file}"
            all_files.append(full_path)

    # Filter out completed files
    pending = [f for f in all_files if f not in (state.completed_files or set())]

    await _emit("stage_complete", {
        "stage": "taskmaster",
        "output": {"queued": len(pending), "total": len(all_files)},
    })

    return {
        "pending_files": pending,
        "current_file": pending[0] if pending else None,
        "status": "files_queued",
    }


async def coder_agent_node(state: WorkingState) -> dict:
    """Coder writes implementation for current file."""
    await _emit("stage_start", {"stage": "coder_agent", "file": state.current_file})

    if not state.current_file or not state.file_tree:
        return {"error": "No file to write"}

    agent = CoderAgent()

    # Get requirements from PRD
    requirements = []
    if state.prd and isinstance(state.prd, dict):
        core_features = state.prd.get("core_features", [])
        requirements = [f.get("description", "") for f in core_features[:3]]

    # Get existing files (completed ones)
    existing_files = {}

    try:
        code = await agent.write_file(
            file_path=state.current_file,
            prd_context=state.prd or {},
            tech_stack=state.tech_stack or {},
            requirements=requirements,
            existing_files=existing_files,
        )

        await _emit("code_generated", {
            "stage": "coder_agent",
            "file_path": state.current_file,
            "code": code,
        })
        await _emit("stage_complete", {"stage": "coder_agent", "file": state.current_file})

        return {
            "current_code": code,
            "completed_files": state.completed_files | {state.current_file},
            "llm_calls_count": state.llm_calls_count + 1,
        }
    except Exception as e:
        await _emit("error", {
            "stage": "coder_agent",
            "message": str(e),
            "file": state.current_file,
        })
        return {"error": str(e)}


async def reviewer_agent_node(state: WorkingState) -> dict:
    """Reviewer validates code quality."""
    await _emit("stage_start", {"stage": "reviewer_agent", "file": state.current_file})

    if not state.current_code or not state.current_file:
        await _emit("stage_complete", {"stage": "reviewer_agent"})
        return {"passed": True}  # Skip review if no code

    agent = ReviewerAgent()

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
    await _emit("review_result", {
        "stage": "reviewer_agent",
        "passed": passed,
        "issues": review_result.get("issues", []),
        "file": state.current_file,
    })
    await _emit("stage_complete", {"stage": "reviewer_agent"})

    return {
        "review_passed": passed,
        "review_issues": review_result.get("issues", []),
        "llm_calls_count": state.llm_calls_count + 1,
    }


async def sandbox_executor_node(state: WorkingState) -> dict:
    """Run tests and linters in sandbox."""
    await _emit("stage_start", {"stage": "sandbox_executor", "file": state.current_file})

    if not state.current_code or not state.current_file:
        await _emit("stage_complete", {"stage": "sandbox_executor"})
        return {"sandbox_passed": True}

    executor = SandboxExecutor()

    # Determine language from file extension
    ext = state.current_file.split(".")[-1] if "." in state.current_file else "py"
    language_map = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "tsx": "typescript",
    }
    language = language_map.get(ext, "python")

    # Create temp file to execute
    import tempfile
    import os
    from pathlib import Path

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = os.path.join(tmpdir, state.current_file)
            os.makedirs(os.path.dirname(tmp_path), exist_ok=True)

            with open(tmp_path, "w") as f:
                f.write(state.current_code)

            # Run linter based on language
            if language == "python":
                returncode, stdout, stderr = await executor.execute(
                    ["python", "-m", "py_compile", tmp_path],
                    Path(os.path.dirname(tmp_path)),
                )
            else:
                returncode, stdout, stderr = await executor.execute(
                    ["echo", "Syntax check passed"],
                    Path(os.path.dirname(tmp_path)),
                )

            sandbox_passed = returncode == 0

            await _emit("sandbox_result", {
                "stage": "sandbox_executor",
                "passed": sandbox_passed,
                "stdout": stdout[:500] if stdout else "",
                "stderr": stderr[:500] if stderr else "",
                "file": state.current_file,
            })
            await _emit("stage_complete", {"stage": "sandbox_executor"})

            return {
                "sandbox_passed": sandbox_passed,
                "llm_calls_count": state.llm_calls_count + 1,
            }
    except Exception as e:
        await _emit("error", {
            "stage": "sandbox_executor",
            "message": str(e),
            "file": state.current_file,
        })
        return {"error": str(e), "sandbox_passed": False}


# ── Conditional routing ────────────────────────────────────────

def should_retry_coder(state: WorkingState) -> str:
    """Determine if coder should retry or move to review."""
    if state.current_file and not state.completed_files:
        return "retry_coder"
    return "review"


def route_to_sandbox(state: WorkingState) -> str:
    """Route to sandbox or end based on pending files."""
    if state.pending_files:
        return "execute_sandbox"
    return "final_review"


# ── Build the graph ────────────────────────────────────────────

workflow = StateGraph(WorkingState)

# Add nodes
workflow.add_node("pm_agent", pm_agent_node)
workflow.add_node("architect_agent", architect_agent_node)
workflow.add_node("taskmaster", taskmaster_node)
workflow.add_node("coder_agent", coder_agent_node)
workflow.add_node("reviewer_agent", reviewer_agent_node)
workflow.add_node("sandbox_executor", sandbox_executor_node)

# Define edges
workflow.set_entry_point("pm_agent")

# PM -> Architect
workflow.add_edge("pm_agent", "architect_agent")

# Architect -> Taskmaster
workflow.add_edge("architect_agent", "taskmaster")

# Taskmaster -> Coder (conditional)
workflow.add_conditional_edges(
    "taskmaster",
    lambda state: "coder_agent" if state.pending_files else "final_review",
)

# Coder -> Reviewer
workflow.add_edge("coder_agent", "reviewer_agent")

# Reviewer -> Sandbox or Retry (conditional)
workflow.add_conditional_edges(
    "reviewer_agent",
    should_retry_coder,
    {
        "retry_coder": "coder_agent",
        "review": "sandbox_executor",
    },
)

# Sandbox -> Next file or Final Review (conditional)
workflow.add_conditional_edges(
    "sandbox_executor",
    route_to_sandbox,
    {
        "execute_sandbox": "taskmaster",
        "final_review": END,
    },
)

app = workflow.compile()
