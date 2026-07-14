from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


def run_command(command: dict, default_timeout: int) -> dict:
    command_id = str(command.get("id", "unknown"))
    if command.get("skip"):
        return {
            "id": command_id,
            "status": "skipped",
            "exit_code": None,
            "duration_ms": 0,
            "stdout": "",
            "stderr": "",
            "timeout": False,
            "reason": str(command.get("reason", "Skipped by command plan.")),
        }
    args = command.get("args")
    if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
        return {
            "id": command_id,
            "status": "failed",
            "exit_code": None,
            "duration_ms": 0,
            "stdout": "",
            "stderr": "",
            "timeout": False,
            "reason": "Invalid command plan entry.",
        }
    started = time.perf_counter()
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=int(command.get("timeout_seconds") or default_timeout))
        return {
            "id": command_id,
            "status": "completed" if proc.returncode == 0 else "failed",
            "exit_code": proc.returncode,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "timeout": False,
            "reason": None,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "id": command_id,
            "status": "timeout",
            "exit_code": None,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timeout": True,
            "reason": "Command timed out.",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    results = []
    for command in plan.get("commands", []):
        result = run_command(command, args.timeout)
        results.append(result)
        if result["status"] in {"failed", "timeout"} and result["id"] == "setup":
            break

    Path("/results").mkdir(parents=True, exist_ok=True)
    Path("/results/results.json").write_text(json.dumps({"commands": results}), encoding="utf-8")
    return 1 if any(item["status"] == "timeout" for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
