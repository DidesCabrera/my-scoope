#!/usr/bin/env python3
"""Manage the machine-local parallel-work registry without mutating Git or processes."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Iterator


STATES = (
    "planned",
    "active",
    "validation",
    "published",
    "integrated",
    "archive-ready",
    "cleaned",
    "blocked",
    "abandoned",
)


def timestamp() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def git_common_dir(repo: pathlib.Path) -> pathlib.Path:
    completed = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(repo), "rev-parse", "--git-common-dir"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
    )
    if completed.returncode != 0:
        raise ValueError(f"{repo} is not inside a Git worktree")
    common = pathlib.Path(completed.stdout.strip())
    return common.resolve() if common.is_absolute() else (repo / common).resolve()


def state_path(repo: pathlib.Path) -> pathlib.Path:
    return git_common_dir(repo) / "codex" / "parallel-work-state.json"


def empty_state() -> dict:
    return {"version": 1, "updated_at": timestamp(), "works": {}, "metro_leases": {}}


@contextlib.contextmanager
def locked_state(repo: pathlib.Path, write: bool) -> Iterator[tuple[pathlib.Path, dict]]:
    path = state_path(repo)
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(".lock")
    if not write and not path.exists():
        yield path, empty_state()
        return
    with lock_path.open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX if write else fcntl.LOCK_SH)
        if path.exists():
            state = json.loads(path.read_text(encoding="utf-8"))
        else:
            state = empty_state()
        yield path, state
        if write:
            state["updated_at"] = timestamp()
            descriptor, temporary_name = tempfile.mkstemp(
                prefix="parallel-work-", suffix=".json", dir=path.parent
            )
            temporary = pathlib.Path(temporary_name)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                    json.dump(state, output, indent=2, sort_keys=True)
                    output.write("\n")
                    output.flush()
                    os.fsync(output.fileno())
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)


def print_state(path: pathlib.Path, state: dict) -> None:
    print(json.dumps({"path": str(path), **state}, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Path inside the Git repository")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init")
    subparsers.add_parser("show")

    register = subparsers.add_parser("register-work")
    register.add_argument("--id", required=True)
    register.add_argument("--owner", required=True)
    register.add_argument("--branch", required=True)
    register.add_argument("--worktree", help="Absolute or relative checkout path when one exists")
    register.add_argument("--base", required=True)
    register.add_argument("--target", required=True)
    register.add_argument("--status", required=True, choices=STATES)
    register.add_argument("--note")

    set_status = subparsers.add_parser("set-status")
    set_status.add_argument("--id", required=True)
    set_status.add_argument("--status", required=True, choices=STATES)

    claim = subparsers.add_parser("claim-metro")
    claim.add_argument("--work-id", required=True)
    claim.add_argument("--port", required=True, type=int)
    claim.add_argument("--environment", required=True)
    claim.add_argument("--pid", type=int)
    claim.add_argument("--device")
    claim.add_argument("--force", action="store_true")

    release = subparsers.add_parser("release-metro")
    release.add_argument("--port", required=True, type=int)
    release.add_argument("--work-id", required=True)

    args = parser.parse_args()
    repo = pathlib.Path(args.repo).expanduser().resolve()
    write = args.command != "show"
    try:
        with locked_state(repo, write=write) as (path, state):
            if args.command == "register-work":
                previous = state["works"].get(args.id, {})
                created_at = previous.get("created_at", timestamp())
                state["works"][args.id] = {
                    "owner": args.owner,
                    "branch": args.branch,
                    "worktree": (
                        str(pathlib.Path(args.worktree).expanduser().resolve())
                        if args.worktree
                        else None
                    ),
                    "base": args.base,
                    "target": args.target,
                    "status": args.status,
                    "created_at": created_at,
                    "updated_at": timestamp(),
                    "note": args.note,
                }
            elif args.command == "set-status":
                if args.id not in state["works"]:
                    raise ValueError(f"unknown work ID: {args.id}")
                state["works"][args.id]["status"] = args.status
                state["works"][args.id]["updated_at"] = timestamp()
            elif args.command == "claim-metro":
                if args.work_id not in state["works"]:
                    raise ValueError(f"unknown work ID: {args.work_id}")
                key = str(args.port)
                current = state["metro_leases"].get(key)
                if current and current["work_id"] != args.work_id and not args.force:
                    raise ValueError(
                        f"port {args.port} is leased to {current['work_id']}; use --force only with explicit authorization"
                    )
                state["metro_leases"][key] = {
                    "work_id": args.work_id,
                    "environment": args.environment,
                    "pid": args.pid,
                    "device": args.device,
                    "claimed_at": timestamp(),
                }
            elif args.command == "release-metro":
                key = str(args.port)
                current = state["metro_leases"].get(key)
                if not current:
                    raise ValueError(f"port {args.port} has no lease")
                if current["work_id"] != args.work_id:
                    raise ValueError(f"port {args.port} is leased to {current['work_id']}")
                del state["metro_leases"][key]
            print_state(path, state)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
