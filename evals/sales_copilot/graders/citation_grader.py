"""Checks structured citation metadata without parsing answer text."""

from collections.abc import Iterable, Mapping


def grade_citations(citations: Iterable[Mapping[str, object]], allowed_sources: set[str]) -> list[str]:
    names = {str(item.get("source") or item.get("name") or "") for item in citations}
    if not names:
        return ["expected at least one structured citation"]
    return [f"citation source not allowed: {name}" for name in sorted(names) if name not in allowed_sources]
