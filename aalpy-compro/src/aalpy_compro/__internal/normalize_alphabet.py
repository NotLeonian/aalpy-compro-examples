from collections.abc import Hashable, Iterable, Iterator
from typing import TypeVar

T = TypeVar("T", bound=Hashable)


def require_hashable(value: Hashable, *, obj_name: str) -> None:
    try:
        hash(value)
    except TypeError as e:
        raise TypeError(f"{obj_name} must be hashable.") from e


def normalize_alphabet(alphabet: T, *, path: str) -> tuple[T, ...]:
    if isinstance(alphabet, (str, bytes)):
        raise ValueError(f"`alphabet` must be a non-string iterable in {path}.")
    if isinstance(alphabet, Iterator):
        raise ValueError(
            f"`alphabet` must be re-iterable in {path}; generators/iterators are not allowed."
        )
    if not isinstance(alphabet, Iterable):
        raise ValueError(f"`alphabet` must be a non-string iterable in {path}.")

    try:
        normalized = tuple(alphabet)
    except TypeError as e:
        raise ValueError(f"`alphabet` must be a non-string iterable in {path}.") from e

    for i, symbol in enumerate(normalized):
        require_hashable(symbol, obj_name=f"`alphabet[{i}]` in {path}")

    return normalized
