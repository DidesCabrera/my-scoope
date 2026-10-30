#!/usr/bin/env python3
"""Produce a read-only Markdown audit of parallel Git and Metro/Expo work."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
from dataclasses import dataclass


READ_ONLY_ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}


def run(
    command: list[str], cwd: pathlib.Path | None = None, timeout: int | None = None
) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=READ_ONLY_ENV,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired) as error:
        return 127, str(error)
    return completed.returncode, completed.stdout.strip()


def git(repo: pathlib.Path, *args: str) -> tuple[int, str]:
    return run(["git", "--no-optional-locks", "-C", str(repo), *args])


def short(value: str, length: int = 12) -> str:
    return value[:length] if value else "unknown"


def cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ") or "—"


def command_summary(command: str, limit: int = 140) -> str:
    compact = " ".join(command.split())
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def ref_exists(repo: pathlib.Path, ref: str) -> bool:
    return git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{ref}")[0] == 0 or git(
        repo, "show-ref", "--verify", "--quiet", f"refs/remotes/{ref}"
    )[0] == 0


def resolve_comparison_ref(repo: pathlib.Path, name: str) -> str | None:
    for candidate in (f"origin/{name}", name):
        if ref_exists(repo, candidate):
            return candidate
    return None


def remote_heads(repo: pathlib.Path, remote: str, names: list[str]) -> tuple[dict[str, str], str | None]:
    refs = [f"refs/heads/{name}" for name in names]
    code, output = run(
        [
            "git",
            "--no-optional-locks",
            "-C",
            str(repo),
            "ls-remote",
            "--exit-code",
            remote,
            *refs,
        ],
        timeout=15,
    )
    if code != 0:
        return {}, output or f"unable to query {remote}"
    result: dict[str, str] = {}
    for line in output.splitlines():
        sha, separator, ref = line.partition("\t")
        if separator and ref.startswith("refs/heads/"):
            result[ref.removeprefix("refs/heads/")] = sha
    return result, None


def local_ref_sha(repo: pathlib.Path, ref: str) -> str | None:
    code, output = git(repo, "rev-parse", "--verify", ref)
    return output if code == 0 else None


def registry_state(repo: pathlib.Path) -> tuple[pathlib.Path | None, dict | None, str | None]:
    code, common_output = git(repo, "rev-parse", "--git-common-dir")
    if code != 0:
        return None, None, common_output or "Git common directory unavailable"
    common = pathlib.Path(common_output)
    if not common.is_absolute():
        common = (repo / common).resolve()
    path = common / "codex" / "parallel-work-state.json"
    if not path.exists():
        return path, None, None
    try:
        return path, json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, json.JSONDecodeError) as error:
        return path, None, str(error)


def divergence(repo: pathlib.Path, left: str, right: str) -> str:
    code, output = git(repo, "rev-list", "--left-right", "--count", f"{left}...{right}")
    if code != 0:
        return "unknown"
    parts = output.split()
    return f"+{parts[0]}/-{parts[1]}" if len(parts) == 2 else "unknown"


def ancestor(repo: pathlib.Path, branch: str, target: str | None) -> str:
    if target is None:
        return "unknown"
    code, _ = git(repo, "merge-base", "--is-ancestor", branch, target)
    return "yes" if code == 0 else "no" if code == 1 else "unknown"


@dataclass
class Worktree:
    path: pathlib.Path
    head: str = ""
    branch: str = "detached"
    prunable: str = ""


def worktrees(repo: pathlib.Path) -> list[Worktree]:
    code, output = git(repo, "worktree", "list", "--porcelain")
    if code != 0:
        raise RuntimeError(output or "git worktree list failed")
    items: list[Worktree] = []
    current: Worktree | None = None
    for line in [*output.splitlines(), ""]:
        if line.startswith("worktree "):
            current = Worktree(path=pathlib.Path(line.removeprefix("worktree ")))
        elif current and line.startswith("HEAD "):
            current.head = line.removeprefix("HEAD ")
        elif current and line.startswith("branch refs/heads/"):
            current.branch = line.removeprefix("branch refs/heads/")
        elif current and line == "detached":
            current.branch = "detached"
        elif current and line.startswith("prunable"):
            current.prunable = line.removeprefix("prunable").strip() or "yes"
        elif not line and current:
            items.append(current)
            current = None
    return items


def status_for(path: pathlib.Path) -> tuple[str, str, str]:
    if not path.is_dir():
        return "missing", "unknown", "unknown"
    code, output = git(path, "status", "--porcelain=v1", "--branch", "--untracked-files=normal")
    if code != 0:
        return "error", "unknown", "unknown"
    lines = output.splitlines()
    header = lines[0] if lines and lines[0].startswith("## ") else ""
    cleanliness = "clean" if len(lines) <= 1 else f"dirty ({len(lines) - 1} entries)"
    upstream = "none"
    branch_divergence = "—"
    if "..." in header:
        tracking = header.split("...", 1)[1]
        upstream = tracking.split(" ", 1)[0]
        if "[" in header and "]" in header:
            branch_divergence = header.split("[", 1)[1].split("]", 1)[0]
    return cleanliness, upstream, branch_divergence


def local_branches(repo: pathlib.Path) -> list[dict[str, str]]:
    fmt = "%(refname:short)%00%(upstream:short)%00%(worktreepath)%00%(objectname)"
    code, output = git(repo, "for-each-ref", f"--format={fmt}", "refs/heads")
    if code != 0:
        raise RuntimeError(output or "git for-each-ref failed")
    result = []
    for line in output.splitlines():
        parts = line.split("\0")
        if len(parts) == 4:
            result.append(dict(zip(("branch", "upstream", "worktree", "head"), parts)))
    return result


def collapse_processes(processes: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], dict[str, list[str] | str]] = {}
    for process in processes:
        key = (process["cwd"], process["command"])
        group = grouped.setdefault(
            key,
            {"pids": [], "ports": [], "cwd": process["cwd"], "command": process["command"]},
        )
        pids = group["pids"]
        ports = group["ports"]
        if isinstance(pids, list):
            pids.append(process["pid"])
        if isinstance(ports, list) and process["ports"] != "unknown":
            ports.extend(part.strip() for part in process["ports"].split(",") if part.strip())
    result = []
    for group in grouped.values():
        pids = group["pids"]
        ports = group["ports"]
        result.append(
            {
                "pid": ",".join(sorted(pids, key=int)) if isinstance(pids, list) else "unknown",
                "ports": ", ".join(sorted(set(ports))) if isinstance(ports, list) and ports else "unknown",
                "cwd": str(group["cwd"]),
                "command": str(group["command"]),
            }
        )
    return result


def metro_processes() -> tuple[list[dict[str, str]], str | None]:
    code, output = run(["ps", "-axo", "pid=,command="])
    if code != 0:
        lsof_code, lsof_output = run(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"])
        if lsof_code != 0:
            return [], output or lsof_output or "process inspection unavailable"
        candidates: dict[str, dict[str, str | list[str]]] = {}
        for line in lsof_output.splitlines()[1:]:
            parts = line.split(None, 8)
            if len(parts) < 9 or parts[0].lower() != "node" or not parts[1].isdigit():
                continue
            pid = parts[1]
            candidate = candidates.setdefault(pid, {"ports": []})
            ports = candidate["ports"]
            if isinstance(ports, list):
                ports.append(parts[8])
        fallback_matches = []
        for pid, candidate in candidates.items():
            cwd = "unknown"
            cwd_code, cwd_output = run(["lsof", "-a", "-p", pid, "-d", "cwd", "-Fn"])
            if cwd_code == 0:
                names = [item[1:] for item in cwd_output.splitlines() if item.startswith("n")]
                if names:
                    cwd = names[-1]
            ports = candidate["ports"]
            fallback_matches.append(
                {
                    "pid": pid,
                    "command": "node listener (Metro/Expo candidate; full command unavailable)",
                    "cwd": cwd,
                    "ports": ", ".join(sorted(set(ports))) if isinstance(ports, list) else "unknown",
                }
            )
        return collapse_processes(fallback_matches), None
    matches = []
    own_pid = os.getpid()
    needles = ("expo start", "metro start", "react-native start", "@expo/cli")
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        pid_text, _, command = stripped.partition(" ")
        if not pid_text.isdigit() or int(pid_text) == own_pid:
            continue
        lowered = command.lower()
        if "audit_parallel_work.py" in lowered or not any(needle in lowered for needle in needles):
            continue
        pid = int(pid_text)
        cwd = "unknown"
        ports = "unknown"
        cwd_code, cwd_output = run(["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"])
        if cwd_code == 0:
            names = [item[1:] for item in cwd_output.splitlines() if item.startswith("n")]
            if names:
                cwd = names[-1]
        port_code, port_output = run(
            ["lsof", "-Pan", "-p", str(pid), "-iTCP", "-sTCP:LISTEN", "-Fn"]
        )
        if port_code == 0:
            found = sorted({item[1:] for item in port_output.splitlines() if item.startswith("n")})
            if found:
                ports = ", ".join(found)
        matches.append(
            {"pid": str(pid), "command": command_summary(command), "cwd": cwd, "ports": ports}
        )
    return collapse_processes(matches), None


def finding(severity: str, message: str) -> str:
    return f"- **{severity}:** {message}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Path inside the Git repository")
    parser.add_argument(
        "--skip-remote",
        action="store_true",
        help="Do not query origin (only for explicit offline diagnostics)",
    )
    args = parser.parse_args()

    requested = pathlib.Path(args.repo).expanduser().resolve()
    code, root_output = git(requested, "rev-parse", "--show-toplevel")
    if code != 0:
        print(f"error: {requested} is not inside a Git worktree", file=sys.stderr)
        return 2
    repo = pathlib.Path(root_output).resolve()
    timestamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    staging_ref = resolve_comparison_ref(repo, "staging")
    main_ref = resolve_comparison_ref(repo, "main")
    if args.skip_remote:
        remote_refs, remote_error = {}, "remote query explicitly skipped"
    else:
        remote_refs, remote_error = remote_heads(repo, "origin", ["staging", "main"])

    try:
        wt_items = worktrees(repo)
        branch_items = local_branches(repo)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    processes, process_error = metro_processes()
    registry_path, registry, registry_error = registry_state(repo)

    print("# Parallel work audit")
    print()
    print(f"- Repository: `{repo}`")
    print(f"- Generated: `{timestamp}`")
    print(f"- Comparison refs: staging=`{staging_ref or 'unavailable'}`, main=`{main_ref or 'unavailable'}`")
    print("- Remote method: direct read-only `ls-remote`; **no fetch was performed**")
    print()
    print("## Remote base freshness")
    print()
    print("| Branch | Remote head | Cached origin ref | Status |")
    print("| --- | --- | --- | --- |")
    remote_statuses: dict[str, str] = {}
    for name in ("staging", "main"):
        remote_sha = remote_refs.get(name)
        cached_sha = local_ref_sha(repo, f"origin/{name}")
        if remote_sha and cached_sha:
            status = "current" if remote_sha == cached_sha else "cached ref differs"
        elif remote_sha:
            status = "cached ref unavailable"
        else:
            status = "remote unknown"
        remote_statuses[name] = status
        print(
            f"| `{name}` | `{short(remote_sha or '')}` | `{short(cached_sha or '')}` | {status} |"
        )
    if remote_error:
        print()
        print(f"Remote query note: `{cell(remote_error)}`")
    print()
    print("## Worktrees")
    print()
    print("| Path | Branch | HEAD | State | Upstream | Divergence | Prunable |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    worktree_states: dict[str, str] = {}
    findings: list[str] = []
    for name, status in remote_statuses.items():
        if status != "current":
            findings.append(
                finding("Medium", f"Remote freshness for `{name}` is not confirmed: {status}.")
            )
    for item in wt_items:
        cleanliness, upstream, branch_divergence = status_for(item.path)
        worktree_states[str(item.path)] = cleanliness
        print(
            f"| `{cell(str(item.path))}` | `{cell(item.branch)}` | `{short(item.head)}` | "
            f"{cell(cleanliness)} | `{cell(upstream)}` | {cell(branch_divergence)} | {cell(item.prunable or 'no')} |"
        )
        if cleanliness == "missing":
            findings.append(finding("High", f"Registered worktree path is missing: `{item.path}`."))
        elif cleanliness.startswith("dirty") and item.branch == "detached":
            findings.append(finding("High", f"Detached worktree `{item.path}` is {cleanliness}."))
        elif cleanliness.startswith("dirty"):
            findings.append(finding("Medium", f"Worktree `{item.path}` on `{item.branch}` is {cleanliness}."))
        if item.prunable:
            findings.append(finding("Medium", f"Worktree `{item.path}` is marked prunable: {item.prunable}."))

    print()
    print("## Local branches")
    print()
    print("| Branch | Upstream | Checked out at | Ahead/behind upstream | In staging locally | In main locally |")
    print("| --- | --- | --- | --- | --- | --- |")
    branches_without_upstream: list[str] = []
    locally_reachable: list[str] = []
    divergent_checked_out: list[str] = []
    for item in branch_items:
        upstream = item["upstream"] or "none"
        upstream_divergence = divergence(repo, item["branch"], upstream) if item["upstream"] else "unknown"
        in_staging = ancestor(repo, item["branch"], staging_ref)
        in_main = ancestor(repo, item["branch"], main_ref)
        print(
            f"| `{cell(item['branch'])}` | `{cell(upstream)}` | `{cell(item['worktree'] or 'not checked out')}` | "
            f"{cell(upstream_divergence)} | {in_staging} | {in_main} |"
        )
        if not item["upstream"] and item["branch"] not in {"main", "staging"}:
            branches_without_upstream.append(item["branch"])
        if not item["worktree"] and in_staging == "yes" and item["branch"] not in {"main", "staging"}:
            locally_reachable.append(item["branch"])
        if item["worktree"] and upstream_divergence not in {"unknown", "+0/-0"}:
            divergent_checked_out.append(f"`{item['branch']}` ({upstream_divergence})")
        if item["worktree"] and worktree_states.get(item["worktree"], "").startswith("dirty"):
            findings.append(finding("Info", f"Branch `{item['branch']}` is checked out in a dirty worktree."))

    if divergent_checked_out:
        findings.append(
            finding("Medium", "Checked-out branch divergence needs review: " + ", ".join(divergent_checked_out) + ".")
        )
    if branches_without_upstream:
        findings.append(
            finding(
                "Medium",
                f"{len(branches_without_upstream)} local branches have no configured upstream; publication state is unknown: "
                + ", ".join(f"`{name}`" for name in branches_without_upstream)
                + ".",
            )
        )
    if locally_reachable:
        findings.append(
            finding(
                "Info",
                f"{len(locally_reachable)} non-checked-out branches are locally reachable from the staging comparison ref and are candidates for ownership/cleanup review; this does not authorize deletion: "
                + ", ".join(f"`{name}`" for name in locally_reachable)
                + ".",
            )
        )

    print()
    print("## Operational registry")
    print()
    if registry_error:
        print(f"Registry unreadable: `{cell(registry_error)}`")
        findings.append(finding("High", "The operational registry exists but cannot be read."))
    elif registry is None:
        print(f"No registry initialized at `{registry_path}`.")
        findings.append(finding("Medium", "No shared operational registry is initialized."))
    else:
        print(f"Registry: `{registry_path}`")
        print()
        print("| Work ID | Owner | Status | Branch | Worktree | Base | Target | Note |")
        print("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for work_id, work in sorted(registry.get("works", {}).items()):
            print(
                f"| `{cell(work_id)}` | {cell(str(work.get('owner', 'unknown')))} | "
                f"{cell(str(work.get('status', 'unknown')))} | `{cell(str(work.get('branch', 'unknown')))}` | "
                f"`{cell(str(work.get('worktree', 'unknown')))}` | `{short(str(work.get('base', '')))}` | "
                f"`{cell(str(work.get('target', 'unknown')))}` | {cell(str(work.get('note') or '—'))} |"
            )
            worktree_value = work.get("worktree")
            registered_path = pathlib.Path(str(worktree_value)) if worktree_value else None
            if (
                work.get("status") in {"active", "validation", "published"}
                and (registered_path is None or not registered_path.is_dir())
            ):
                findings.append(
                    finding("High", f"Registered active work `{work_id}` has no existing worktree (`{registered_path or 'none'}`).")
                )
        leases = registry.get("metro_leases", {})
        print()
        if leases:
            print("Metro leases:")
            for port, lease in sorted(leases.items()):
                print(
                    f"- Port `{port}` → work `{lease.get('work_id', 'unknown')}`, environment "
                    f"`{lease.get('environment', 'unknown')}`, PID `{lease.get('pid') or 'unknown'}`, "
                    f"device `{lease.get('device') or 'unknown'}`."
                )
        else:
            print("Metro leases: none.")

    print()
    print("## Metro / Expo processes")
    print()
    if process_error:
        print(f"Process inspection unavailable: `{cell(process_error)}`")
        findings.append(finding("Medium", "Metro/Expo process state is unknown because process inspection was unavailable."))
    elif processes:
        print("| PID | Working directory | Listening endpoints | Command |")
        print("| --- | --- | --- | --- |")
        known_worktree_paths = [item.path.resolve() for item in wt_items if item.path.is_dir()]
        for process in processes:
            print(
                f"| {process['pid']} | `{cell(process['cwd'])}` | `{cell(process['ports'])}` | "
                f"`{cell(process['command'])}` |"
            )
            if process["cwd"] == "unknown":
                findings.append(finding("Medium", f"Metro/Expo PID {process['pid']} could not be attributed to a checkout."))
            else:
                process_path = pathlib.Path(process["cwd"]).resolve()
                if not any(process_path == path or path in process_path.parents for path in known_worktree_paths):
                    findings.append(
                        finding(
                            "High",
                            f"Metro/Expo candidate PID {process['pid']} runs from `{process_path}`, which is not inside a worktree registered by this repository.",
                        )
                    )
        if len(processes) > 1:
            findings.append(finding("High", f"{len(processes)} distinct Metro/Expo sessions were detected; verify which checkout and port each client uses."))
    else:
        print("No matching local Metro/Expo process was detected.")

    print()
    print("## Findings")
    print()
    if findings:
        for item in findings:
            print(item)
    else:
        print("- **Info:** No material local coordination risks were detected.")

    print()
    print("## Limits and next steps")
    print()
    if all(status == "current" for status in remote_statuses.values()):
        print("- Cached `origin/staging` and `origin/main` match the directly queried remote heads.")
    else:
        print("- One or more cached base refs could not be confirmed against the remote.")
    print("- The audit never fetches; if a remote head differs, ancestry against that newer commit remains unknown locally.")
    print("- Local ancestry does not prove pull-request merge or deployment state.")
    print("- Missing upstream, age, or local reachability alone never authorizes branch deletion.")
    print("- Review authoritative PR/task ownership and ignored operational files before any cleanup plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
