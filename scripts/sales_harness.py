"""Run deterministic Sales Copilot checks and write a compact JSON report."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "sales_harness" / "report.json"
UNIT = "backend/tests/unit/sales_copilot"
INTEGRATION = "backend/tests/integration/tests/sales_copilot"
V1_UNIT = "backend/tests/unit/sales_copilot/test_harness_invariants.py"
V1_INTEGRATION = "backend/tests/integration/tests/sales_copilot/test_sales_copilot_api.py"
MULTI_AGENT_UNIT = "backend/tests/unit/sales_copilot/test_deal_council.py"
MULTI_AGENT_INTEGRATION = "backend/tests/integration/tests/sales_copilot/test_deal_council.py"


@dataclass
class Check:
    name: str
    status: str
    detail: str
    command: list[str]


def run_check(
    name: str, command: list[str], environment: dict[str, str] | None = None
) -> Check:
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, **(environment or {})},
        )
    except FileNotFoundError as exc:
        return Check(name, "FAIL", f"required executable is unavailable: {exc.filename}", command)
    detail = (result.stdout + result.stderr).strip()[-4000:]
    return Check(name, "PASS" if result.returncode == 0 else "FAIL", detail, command)


def pytest_command(target: str) -> list[str]:
    if shutil.which("uv"):
        return ["uv", "run", "pytest", "-q", target]
    if pytest := shutil.which("pytest"):
        return [pytest, "-q", target]
    return [sys.executable, "-m", "pytest", "-q", target]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fast", action="store_true", help="Run structural and unit checks only.")
    parser.add_argument("--integration", action="store_true", help="Include PostgreSQL-backed API tests.")
    parser.add_argument("--multi-agent", action="store_true", help="Run focused Deal Council checks.")
    parser.add_argument("--live-agent", action="store_true", help="Record live Agent evals as optional and require configured services.")
    args = parser.parse_args()

    checks = [run_check("eval_definitions", [sys.executable, "evals/sales_copilot/run.py"])]
    if args.multi_agent:
        checks.append(run_check("multi_agent_unit", pytest_command(MULTI_AGENT_UNIT)))
    else:
        checks.append(run_check("static_and_unit", pytest_command(UNIT)))
        checks.append(run_check("multi_agent_routing_conflict", pytest_command(MULTI_AGENT_UNIT)))
    if (args.integration or not args.fast) and not args.multi_agent:
        checks.append(
            run_check(
                "postgres_api_integration",
                pytest_command(V1_INTEGRATION),
                # Sales API tests do not index documents. Reuse Onyx's lite mode
                # to avoid the generic integration fixture's unrelated worker fleet.
                {
                    "DEV_MODE": "true",
                    "DISABLE_VECTOR_DB": "true",
                    "FILE_STORE_BACKEND": "postgres",
                },
            )
        )
    if args.multi_agent or (args.integration or not args.fast):
        checks.append(
            run_check(
                "multi_agent_mutation_safety",
                pytest_command(MULTI_AGENT_INTEGRATION),
                {
                    "DEV_MODE": "true",
                    "DISABLE_VECTOR_DB": "true",
                    "FILE_STORE_BACKEND": "postgres",
                },
            )
        )
    if args.live_agent:
        checks.append(
            Check(
                "live_agent",
                "SKIPPED_EXTERNAL",
                "Live Agent trace and provider configuration are environment-specific.",
                [],
            )
        )

    status = "PASS" if all(check.status == "PASS" for check in checks) else "FAIL"
    if any(check.status == "SKIPPED_EXTERNAL" for check in checks) and status == "PASS":
        status = "PASS_WITH_SKIPS"
    summary = {
        "total": len(checks),
        "passed": sum(check.status == "PASS" for check in checks),
        "failed": sum(check.status == "FAIL" for check in checks),
        "skipped": sum(check.status == "SKIPPED_EXTERNAL" for check in checks),
    }
    report = {"status": status, "summary": summary, "checks": [asdict(check) for check in checks], "failures": [asdict(check) for check in checks if check.status == "FAIL"]}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Sales Copilot Harness")
    print("=" * 48)
    for check in checks:
        print(f"{check.name:28} {check.status}")
    print("-" * 48)
    print(f"HARNESS STATUS: {status}")
    print(f"REPORT: {REPORT.relative_to(ROOT)}")
    return 0 if status in {"PASS", "PASS_WITH_SKIPS"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
