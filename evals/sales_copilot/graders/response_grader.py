"""Rule-based answer checks for deterministic Sales facts."""


def grade_response(response: str, required_facts: list[str]) -> list[str]:
    normalized = response.casefold()
    return [fact for fact in required_facts if fact.casefold() not in normalized]
