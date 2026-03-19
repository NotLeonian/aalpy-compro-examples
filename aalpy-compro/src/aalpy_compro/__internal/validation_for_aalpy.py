from collections.abc import Hashable, Iterable, Sequence
from typing import TypeVar, cast

from .learning_property import WordFactory

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


def validate_aalpy_word(
    raw_word: Iterable[T],
    *,
    source_name: str,
) -> tuple[T, ...]:
    if isinstance(raw_word, (str, bytes)):
        raise ValueError(
            f"{source_name} must be a non-string iterable of input symbols."
        )

    if not isinstance(raw_word, Iterable):
        raise ValueError(
            f"{source_name} must be a non-string iterable of input symbols."
        )

    try:
        word_tuple = tuple(raw_word)
    except TypeError as e:
        raise ValueError(
            f"{source_name} must be a non-string iterable of input symbols."
        ) from e

    for symbol_index, symbol in enumerate(word_tuple):
        try:
            hash(symbol)
        except TypeError as e:
            raise TypeError(
                f"{source_name} contains an unhashable symbol at index {symbol_index}."
            ) from e

        if symbol is None:
            raise ValueError(
                f"{source_name} contains `None`, but AALpy reserves `None` as the "
                "empty-word / no-input marker."
            )

    return cast(tuple[T, ...], word_tuple)


def wrap_fixed_eq_word_factory_for_aalpy(
    fixed_eq_word_factory: WordFactory[T] | None,
) -> WordFactory[T] | None:
    if fixed_eq_word_factory is None:
        return None

    def wrapped_factory() -> Iterable[tuple[T, ...]]:
        produced = fixed_eq_word_factory()
        if not isinstance(produced, Iterable) or isinstance(produced, (str, bytes)):
            raise ValueError(
                "`fixed_eq_word_factory()` must return a non-string iterable of words."
            )

        for word_index, raw_word in enumerate(produced):
            yield validate_aalpy_word(
                raw_word,
                source_name=(
                    f"`fixed_eq_word_factory()` output word at index {word_index}"
                ),
            )

    return wrapped_factory
