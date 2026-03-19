from collections.abc import Hashable, Sequence
from typing import TypeVar

T = TypeVar("T", bound=Hashable)


def validate_aalpy_alphabet(alphabet: Sequence[T]) -> tuple[T, ...]:
    alphabet_tuple = tuple(alphabet)

    try:
        alphabet_set = set(alphabet_tuple)
    except TypeError as e:
        raise ValueError("`alphabet` must contain only hashable symbols.") from e

    if len(alphabet_set) != len(alphabet_tuple):
        raise ValueError("`alphabet` must not contain duplicates.")

    if any(symbol is None for symbol in alphabet_tuple):
        raise ValueError(
            "`None` cannot be used as an input symbol with AALpy-backed functionality, "
            "because AALpy reserves `None` as the empty-word / no-input marker."
        )

    return alphabet_tuple
