"""Validate Sales eval definitions without requiring an LLM provider."""

from __future__ import annotations

import json
from pathlib import Path


CASES_PATH = Path(__file__).with_name("cases.yaml")
REQUIRED_CASES = {"rag_citation", "crm_pipeline", "account_brief", "roi", "mutation_preview", "mutation_confirm"}


def load_cases() -> list[dict[str, object]]:
    """The file uses JSON syntax, which is valid YAML and needs no new parser dependency."""
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ValueError("cases.yaml must contain a cases list")
    return cases


def main() -> int:
    cases = load_cases()
    ids = {str(case.get("id")) for case in cases}
    missing = REQUIRED_CASES - ids
    if missing:
        raise ValueError(f"missing required cases: {sorted(missing)}")
    for case in cases:
        if not case.get("category") or not case.get("required_tool_groups"):
            raise ValueError(f"case is incomplete: {case.get('id')}")
    print(f"Validated {len(cases)} deterministic Sales eval definitions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
