from __future__ import annotations

import argparse
import json
from pathlib import Path

from .karigar.runner import KarigarRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="karigar")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--job-json", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    job_data = json.loads(args.job_json.read_text(encoding="utf-8"))
    runner = KarigarRunner(workspace=args.workspace)
    result = runner.run_job(job_data)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0 if result.status.value == "success" else 1
