#!/usr/bin/env python3
"""Inspect the source, Metro and iOS device used for a mobile preview."""

import argparse
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
from urllib.parse import quote


ROOT = Path(__file__).resolve().parent.parent
DEVICE_FILE = Path.home() / ".config" / "my-scoope" / "preview-simulator"
PORTS = range(8081, 8100)


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False)


def booted_devices() -> list[dict[str, str]]:
    result = run("xcrun", "simctl", "list", "-j", "devices", "booted")
    if result.returncode:
        raise RuntimeError("No se pudo consultar CoreSimulator: " + result.stderr.strip())
    groups = json.loads(result.stdout)["devices"].values()
    return [device for group in groups for device in group if device["state"] == "Booted"]


def metro_processes() -> list[tuple[int, int, Path]]:
    result = run("lsof", "-nP", "-iTCP:8081-8099", "-sTCP:LISTEN", "-Fpn")
    if result.returncode not in (0, 1):
        raise RuntimeError("No se pudieron inspeccionar los puertos de Metro.")
    pid = None
    matches = []
    for line in result.stdout.splitlines():
        if line.startswith("p") and line[1:].isdigit():
            pid = int(line[1:])
        elif line.startswith("n") and pid is not None:
            port_match = re.search(r":(\d+)$", line)
            if not port_match:
                continue
            port = int(port_match.group(1))
            if port not in PORTS:
                continue
            cwd = run("lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn")
            path = next((entry[1:] for entry in cwd.stdout.splitlines() if entry.startswith("n/")), None)
            if path:
                matches.append((port, pid, Path(path).resolve()))
    return matches


def free_port(used: set[int]) -> int | None:
    for port in PORTS:
        if port in used:
            continue
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
        return port
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", help="UDID del simulador de revisión")
    parser.add_argument("--remember-device", action="store_true", help="Guardar el UDID para próximas revisiones")
    parser.add_argument("--route", default="/today", help="Ruta interna que se quiere mostrar")
    args = parser.parse_args()
    if not args.route.startswith("/") or args.route.startswith("//") or "\\" in args.route:
        parser.error("--route debe ser una ruta interna que comience con /.")

    devices = booted_devices()
    selected = args.device or os.environ.get("MYSCOOPE_PREVIEW_DEVICE")
    if not selected and DEVICE_FILE.exists():
        selected = DEVICE_FILE.read_text().strip()
    if not selected and len(devices) == 1:
        selected = devices[0]["udid"]
    known = {device["udid"] for device in devices}
    if selected and selected not in known:
        raise RuntimeError(
            f"El simulador de revisión ({selected}) está apagado. "
            f"Enciéndelo con xcrun simctl boot {selected} y vuelve a inspeccionar."
        )
    if args.remember_device:
        if not selected:
            parser.error("Elige un simulador con --device para guardarlo.")
        DEVICE_FILE.parent.mkdir(parents=True, exist_ok=True)
        DEVICE_FILE.write_text(selected + "\n")

    metros = list(dict.fromkeys(metro_processes()))
    matching = [port for port, _, path in metros if path == ROOT / "mobile"]
    proposed = matching[0] if matching else free_port({port for port, _, _ in metros})
    print(f"checkout={ROOT}")
    print(f"branch={run('git', '-C', str(ROOT), 'branch', '--show-current').stdout.strip()}")
    for port, _, path in metros:
        print(f"metro_{port}={path}")
    print(f"matching_metro_port={matching[0] if matching else 'none'}")
    print(f"available_port={proposed if proposed is not None else 'none'}")
    for device in devices:
        print(f"booted_device={device['name']}|{device['udid']}")
    print(f"selected_device={selected if selected else ('ambiguous' if devices else 'none')}")
    if selected:
        installed = run("xcrun", "simctl", "get_app_container", selected, "com.myscoope.app", "app")
        print(f"development_client_installed={'yes' if installed.returncode == 0 else 'no'}")
    if selected and proposed is not None:
        metro_url = f"http://127.0.0.1:{proposed}"
        print(f"client_url=exp+my-scoope://expo-development-client/?url={quote(metro_url, safe='')}")
        print(f"screen_url=myscoope:///{args.route.lstrip('/')}")
        print(f"login_url=myscoope:///login?returnTo={quote(args.route, safe='')}")
    if len(devices) > 1 and not selected:
        print("action=Elige una vez --device <UDID> --remember-device; hay varios simuladores encendidos.")
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"preview_error={error}", file=sys.stderr)
        raise SystemExit(1)
