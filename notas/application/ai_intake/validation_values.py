"""Value comparisons shared by evaluation trajectories."""

from typing import Any, Iterable, Sequence


def is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def compressed_values(values: Iterable[Any]) -> list[Any]:
    compressed: list[Any] = []
    for value in values:
        if is_empty(value):
            continue
        if not compressed or compressed[-1] != value:
            compressed.append(value)
    return compressed


def is_subsequence(expected: Sequence[Any], actual: Sequence[Any]) -> bool:
    iterator = iter(actual)
    return all(any(candidate == expected_value for candidate in iterator) for expected_value in expected)


def first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""
