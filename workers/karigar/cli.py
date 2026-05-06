from __future__ import annotations

import argparse
import json
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runner = KarigarRunner(workspace=args.workspace)

    if args.backend:
        if not args.worker_id:
            print("Error: --worker-id is required for --backend mode", file=__import__("sys").stderr)
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
                print(f"Worker registration failed: {exc}", file=__import__("sys").stderr)
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
        print("Error: --job-json is required (or use --backend for worker mode)", file=__import__("sys").stderr)
        return 1

    job_data = json.loads(args.job_json.read_text(encoding="utf-8"))
    result = runner.run_job(job_data)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.status.value == "success" else 1
