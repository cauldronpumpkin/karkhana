from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .karigar.runner import KarigarRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="karigar")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--job-json", type=Path, default=None)
    parser.add_argument("--backend", action="store_true", help="Run in backend-connected worker mode")
    parser.add_argument("--api-base", type=str, default="https://api.karkhana.one", help="Backend API base URL")
    parser.add_argument("--worker-id", type=str, default="", help="Worker ID for backend mode")
    parser.add_argument("--worker-token", type=str, default="", help="Worker auth token for backend mode")
    parser.add_argument("--poll-interval", type=float, default=5.0, help="Seconds between job polls")
    parser.add_argument("--max-jobs", type=int, default=0, help="Max jobs before exit (0=forever)")
    parser.add_argument("--factory-run-id", type=str, default="", help="Factory run ID for ledger auto-append")
    parser.add_argument("--register", action="store_true", help="Register worker with backend before starting loop")

    # ── Subcommands ──────────────────────────────────────────
    sub = parser.add_subparsers(dest="subcommand", title="subcommands")

    # ── daemon ───────────────────────────────────────────────
    daemon_parser = sub.add_parser(
        "daemon",
        help="Run Karigar as a persistent background daemon",
        description="Run Karigar as a persistent background daemon that polls, "
        "claims, executes, and reports in an infinite loop with graceful "
        "shutdown (SIGTERM/SIGINT), state persistence, heartbeat, and "
        "circuit-breaker protection.",
    )
    daemon_parser.add_argument(
        "--run-once",
        action="store_true",
        help="Execute a single claim-execute-report cycle and exit "
        "(for Windows service / Tauri desktop worker integration)",
    )
    daemon_parser.add_argument(
        "--poll-interval",
        type=float,
        default=20.0,
        help="Seconds between job polls when idle (default: 20)",
    )
    daemon_parser.add_argument(
        "--heartbeat-interval",
        type=float,
        default=15.0,
        help="Seconds between heartbeat calls for in-flight jobs (default: 15)",
    )
    daemon_parser.add_argument(
        "--max-jobs-per-day",
        type=int,
        default=100,
        help="Daily job cap (circuit breaker, default: 100)",
    )
    daemon_parser.add_argument(
        "--max-retries-per-job",
        type=int,
        default=3,
        help="Max retries per job (circuit breaker, default: 3)",
    )
    daemon_parser.add_argument(
        "--token-budget-per-day",
        type=int,
        default=1_000_000,
        help="Estimated token cap per day (circuit breaker, default: 1,000,000)",
    )
    daemon_parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path.home() / ".karigar",
        help="Directory for daemon state file (default: ~/.karigar)",
    )
    daemon_parser.add_argument(
        "--api-base",
        type=str,
        default="https://api.karkhana.one",
        help="Backend API base URL",
    )
    daemon_parser.add_argument(
        "--worker-id",
        type=str,
        default="",
        help="Worker ID (required)",
    )
    daemon_parser.add_argument(
        "--worker-token",
        type=str,
        default="",
        help="Worker auth token",
    )
    daemon_parser.add_argument(
        "--factory-run-id",
        type=str,
        default="",
        help="Factory run ID for ledger auto-append",
    )
    daemon_parser.add_argument(
        "--register",
        action="store_true",
        help="Register worker with backend before starting loop",
    )
    # Sub-subcommand: daemon status
    daemon_subs = daemon_parser.add_subparsers(dest="daemon_action", title="daemon actions")
    status_parser = daemon_subs.add_parser("status", help="Show current daemon state")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # ── daemon subcommand ────────────────────────────────────
    if args.subcommand == "daemon":
        return _run_daemon(args)

    # ── legacy backend / local modes ─────────────────────────
    runner = KarigarRunner(workspace=args.workspace)

    if args.backend:
        if not args.worker_id:
            print("Error: --worker-id is required for --backend mode", file=sys.stderr)
            return 1
        if args.register and args.worker_token:
            from .karigar.backend_client import BackendClient

            client = BackendClient(
                api_base_url=args.api_base,
                worker_id=args.worker_id,
                worker_token=args.worker_token,
            )
            try:
                reg = client.register_worker()
                print(f"Worker registered: {json.dumps(reg, indent=2)}")
            except Exception as exc:
                print(f"Worker registration failed: {exc}", file=sys.stderr)
                return 1
        runner.run_backend_loop(
            api_base_url=args.api_base,
            worker_id=args.worker_id,
            worker_token=args.worker_token,
            poll_interval=args.poll_interval,
            max_jobs=args.max_jobs,
            factory_run_id=args.factory_run_id,
        )
        return 0

    if not args.job_json:
        print("Error: --job-json is required (or use --backend for worker mode)", file=sys.stderr)
        return 1

    job_data = json.loads(args.job_json.read_text(encoding="utf-8"))
    result = runner.run_job(job_data)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.status.value == "success" else 1


def _run_daemon(args: argparse.Namespace) -> int:
    """Handle the ``karigar daemon`` subcommand."""
    from .karigar.backend_client import BackendClient
    from .karigar.circuit_breaker import CircuitBreakerConfig
    from .karigar.daemon import DaemonConfig, DaemonController

    # ── daemon status ────────────────────────────────────────
    if args.daemon_action == "status":
        state_path = args.state_dir / "daemon.json"
        try:
            if state_path.exists():
                data = json.loads(state_path.read_text(encoding="utf-8"))
                print(json.dumps(data, indent=2, sort_keys=True))
            else:
                print(f"No state file found at {state_path}")
                print("Run 'karigar daemon' first to create it.")
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Error reading state file: {exc}", file=sys.stderr)
            return 1
        return 0

    # ── daemon run mode ──────────────────────────────────────
    if not args.worker_id:
        print("Error: --worker-id is required for daemon mode", file=sys.stderr)
        return 1

    # Optional worker registration
    if args.register and args.worker_token:
        client = BackendClient(
            api_base_url=args.api_base,
            worker_id=args.worker_id,
            worker_token=args.worker_token,
        )
        try:
            reg = client.register_worker()
            print(f"Worker registered: {json.dumps(reg, indent=2)}")
        except Exception as exc:
            print(f"Worker registration failed: {exc}", file=sys.stderr)
            return 1

    # Build daemon config
    daemon_config = DaemonConfig(
        poll_interval=args.poll_interval,
        heartbeat_interval=args.heartbeat_interval,
        run_once=args.run_once,
        state_dir=args.state_dir,
    )

    circuit_config = CircuitBreakerConfig(
        max_retries_per_job=args.max_retries_per_job,
        max_jobs_per_day=args.max_jobs_per_day,
        token_budget_per_day=args.token_budget_per_day,
    )

    client = BackendClient(
        api_base_url=args.api_base,
        worker_id=args.worker_id,
        worker_token=args.worker_token,
    )

    runner = KarigarRunner(workspace=Path.cwd())

    controller = DaemonController(
        runner=runner,
        client=client,
        config=daemon_config,
        circuit_config=circuit_config,
        factory_run_id=args.factory_run_id,
    )

    controller.run()
    return 0
