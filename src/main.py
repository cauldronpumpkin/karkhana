"""CLI entry point for the Software Factory."""

import asyncio
import threading
import webbrowser
import uuid

import click

from src.command_center.models import JobReasoningLaunchOptions, ReasoningConfig, resolve_reasoning_config
from src.graph.flow import app
from src.config import config
from src.utils.logger import BuildProgress, log_info, log_success, log_error


DASHBOARD_PORT = 8420


def _start_dashboard_server():
    """Launch the FastAPI dashboard in a background thread."""
    import uvicorn
    from src.dashboard.server import app as dashboard_app

    config = uvicorn.Config(
        dashboard_app,
        host="127.0.0.1",
        port=DASHBOARD_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    server.run()


@click.command()
@click.argument("idea", type=str)
@click.option("--output-dir", "-o", default="generated_project", help="Output directory")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--dashboard", "-d", is_flag=True, help="Launch live web dashboard")
@click.option("--reasoning", type=click.Choice(["on", "off"]), default=None, help="Enable reasoning controls")
@click.option("--reasoning-profile", type=click.Choice(["fast", "balanced", "deep"]), default=None, help="Reasoning preset profile")
@click.option("--tot-paths", type=int, default=None, help="Number of architecture candidates")
@click.option("--critic", type=click.Choice(["on", "off"]), default=None, help="Enable critic pass")
@click.option("--tdd", type=click.Choice(["on", "off"]), default=None, help="Enable test-driven reflection loop")
@click.option("--tdd-split", type=int, default=None, help="Percent time budget for TDD reflection")
@click.option("--thinking-logs", type=click.Choice(["on", "off"]), default=None, help="Expose <thinking> traces in logs")
def main(
    idea: str,
    output_dir: str,
    verbose: bool,
    dashboard: bool,
    reasoning: str | None,
    reasoning_profile: str | None,
    tot_paths: int | None,
    critic: str | None,
    tdd: str | None,
    tdd_split: int | None,
    thinking_logs: str | None,
):
    """Generate a complete codebase from a raw idea."""

    log_info(f"Initializing Software Factory...")
    log_info(f"Idea: {idea}")
    log_info(f"Output directory: {output_dir}")

    # ── Dashboard mode ────────────────────────────────────
    if dashboard:
        log_info(f"Starting dashboard on http://127.0.0.1:{DASHBOARD_PORT}")

        # Start FastAPI server in a daemon thread
        server_thread = threading.Thread(target=_start_dashboard_server, daemon=True)
        server_thread.start()

        # Give the server a moment to bind
        import time
        time.sleep(1.0)

        webbrowser.open(f"http://127.0.0.1:{DASHBOARD_PORT}")

    # ── Run pipeline ──────────────────────────────────────
    progress = BuildProgress()
    progress.start()

    try:
        from src.types.state import WorkingState

        launch_reasoning = JobReasoningLaunchOptions(
            enabled=(reasoning == "on") if reasoning else None,
            profile=reasoning_profile,
            architect_tot_paths=tot_paths,
            critic_enabled=(critic == "on") if critic else None,
            tdd_enabled=(tdd == "on") if tdd else None,
            tdd_time_split_percent=tdd_split,
            thinking_visibility=("logs" if thinking_logs == "on" else "internal") if thinking_logs else None,
        )
        env_reasoning = ReasoningConfig.model_validate(config.reasoning.model_dump())
        resolved_reasoning = resolve_reasoning_config(
            env_defaults=env_reasoning,
            global_defaults=env_reasoning,
            launch_override=launch_reasoning,
        )

        cli_job_id = f"cli-{uuid.uuid4().hex[:8]}"
        state = WorkingState(
            raw_idea=idea,
            dashboard_mode=dashboard,
            job_id=cli_job_id,
            approval_required=False,
            agent_comms_enabled=bool(config.agent_comms.enabled),
            coordination_budget=int(config.agent_comms.max_rounds),
            agent_comms_escalate_blocking_only=bool(config.agent_comms.escalate_blocking_only),
            reasoning_config=resolved_reasoning.model_dump(),
        )

        config = {"configurable": {"thread_id": "1"}}

        async def run_workflow():
            # Emit build_started event
            if dashboard:
                from src.dashboard.event_bus import EventBus
                await EventBus.get().emit("build_started", {"job_id": cli_job_id, "idea": idea})

            result = await app.ainvoke(state.model_dump(), config)

            # Emit build_complete event
            if dashboard:
                from src.dashboard.event_bus import EventBus
                await EventBus.get().emit("build_complete", {
                    "job_id": cli_job_id,
                    "output_dir": output_dir,
                    "files_generated": len(result.get("completed_files", [])),
                    "llm_calls": result.get("llm_calls_count", 0),
                })

            return result

        final_state = asyncio.run(run_workflow())

        progress.update_progress(100)
        progress.stop()

        log_success(f"Build complete! Project saved to {output_dir}")

    except Exception as e:
        progress.stop()
        log_error(f"Build failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
