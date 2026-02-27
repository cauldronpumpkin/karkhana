"""CLI entry point for the Software Factory."""

import asyncio
import threading
import webbrowser
from pathlib import Path

import click

from src.graph.flow import app
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
def main(idea: str, output_dir: str, verbose: bool, dashboard: bool):
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

        state = WorkingState(raw_idea=idea, dashboard_mode=dashboard)

        config = {"configurable": {"thread_id": "1"}}

        async def run_workflow():
            # Emit build_started event
            if dashboard:
                from src.dashboard.event_bus import EventBus
                await EventBus.get().emit("build_started", {"idea": idea})

            result = await app.ainvoke(state.model_dump(), config)

            # Emit build_complete event
            if dashboard:
                from src.dashboard.event_bus import EventBus
                await EventBus.get().emit("build_complete", {
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
