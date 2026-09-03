"""Deterministic checks for normalized Sales tool-call traces."""

from collections.abc import Iterable


def grade_tools(called_tools: Iterable[str], required_tool_groups: list[list[str]], forbidden_tools: Iterable[str] = ()) -> list[str]:
    """Return stable failure messages for required one-of tool groups."""
    called = set(called_tools)
    failures = [f"forbidden tool called: {tool}" for tool in forbidden_tools if tool in called]
    for group in required_tool_groups:
        if not called.intersection(group):
            failures.append(f"expected one of {', '.join(group)}; observed {sorted(called)}")
    return failures
