#!/usr/bin/env python3
"""Lightweight monitor for GitHub Actions workflow runs.

Usage examples:
  python scripts/monitor_github_run.py --run-id 25619909095
  python scripts/monitor_github_run.py --workflow test-wave-1.yml --branch main
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Optional


TERMINAL_STATES = {"completed"}
SUCCESS_CONCLUSIONS = {"success"}


@dataclass
class RunStatus:
    run_id: int
    name: str
    status: str
    conclusion: Optional[str]
    url: str


def run_gh(args: list[str]) -> str:
    cmd = ["gh", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = proc.stderr.strip() or proc.stdout.strip() or "Unknown error"
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{err}")
    return proc.stdout


def get_latest_run_id(workflow: str, branch: str) -> int:
    out = run_gh(
        [
            "run",
            "list",
            "--workflow",
            workflow,
            "--branch",
            branch,
            "--limit",
            "1",
            "--json",
            "databaseId",
        ]
    )
    rows = json.loads(out)
    if not rows:
        raise RuntimeError(
            f"No runs found for workflow '{workflow}' on branch '{branch}'."
        )
    return int(rows[0]["databaseId"])


def get_run_status(run_id: int) -> RunStatus:
    out = run_gh(
        [
            "run",
            "view",
            str(run_id),
            "--json",
            "databaseId,name,status,conclusion,url",
        ]
    )
    row = json.loads(out)
    return RunStatus(
        run_id=int(row["databaseId"]),
        name=row.get("name") or "",
        status=(row.get("status") or "").lower(),
        conclusion=(row.get("conclusion") or "").lower() or None,
        url=row.get("url") or "",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitor a GitHub Actions run at low frequency until completion."
    )
    parser.add_argument(
        "--run-id",
        type=int,
        help="Run ID to monitor directly.",
    )
    parser.add_argument(
        "--workflow",
        help="Workflow file name, for example test-wave-1.yml.",
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Branch used with --workflow (default: main).",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=180,
        help="Polling interval in seconds (default: 180).",
    )
    parser.add_argument(
        "--max-checks",
        type=int,
        default=40,
        help="Max polling attempts before timeout (default: 40).",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.run_id is None and not args.workflow:
        parser.error("Pass either --run-id or --workflow.")

    if args.interval_seconds < 15:
        parser.error("--interval-seconds must be >= 15 to stay low-frequency.")

    if args.max_checks < 1:
        parser.error("--max-checks must be >= 1.")

    try:
        run_id = args.run_id
        if run_id is None:
            run_id = get_latest_run_id(args.workflow, args.branch)
            print(f"Monitoring latest run for workflow '{args.workflow}' on '{args.branch}': {run_id}")

        print(
            f"Monitoring run {run_id} every {args.interval_seconds}s "
            f"for up to {args.max_checks} checks..."
        )

        for attempt in range(1, args.max_checks + 1):
            info = get_run_status(run_id)
            conclusion = info.conclusion or "pending"
            print(
                f"[{attempt}/{args.max_checks}] "
                f"status={info.status} conclusion={conclusion} url={info.url}"
            )

            if info.status in TERMINAL_STATES:
                if info.conclusion in SUCCESS_CONCLUSIONS:
                    print("Run completed successfully.")
                    return 0
                print("Run completed with a non-success conclusion.")
                return 1

            if attempt < args.max_checks:
                time.sleep(args.interval_seconds)

        print("Monitoring timed out before completion.")
        return 2

    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
