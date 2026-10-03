from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar, cast

from ..regex import ComplementRegex, Regex
from .normalize_alphabet import normalize_alphabet
from .property_module import load_property_module

T = TypeVar("T", bound=Hashable)


@dataclass(frozen=True)
class RegexProperty(Generic[T]):
    alphabet: Sequence[T]
    regex: Regex[T] | ComplementRegex[T]
    symbol_to_label: Callable[[T], str] = str


def load_regex_property(path: str) -> RegexProperty[Hashable]:
    """
    必須:
      - alphabet: Sequence[T]
      - regex: Regex[T] | ComplementRegex[T]

    任意:
      - symbol_to_label: Callable[[T], str]
    """

    mod = load_property_module(
        path,
        module_name="regex_property",
        required_attributes=("alphabet", "regex"),
    )

    raw_alphabet = mod.alphabet
    regex = mod.regex
    raw_symbol_to_label = getattr(mod, "symbol_to_label", str)

    if not isinstance(regex, (Regex, ComplementRegex)):
        raise TypeError(
            f"`regex` must be an instance of `aalpy_compro.regex.Regex` or `aalpy_compro.regex.ComplementRegex` in {path}."
        )
    if not callable(raw_symbol_to_label):
        raise TypeError(f"`symbol_to_label` must be callable in {path}.")

    alphabet = normalize_alphabet(raw_alphabet, path=path)
    symbol_to_label = cast(Callable[[Hashable], str], raw_symbol_to_label)

    regex.ensure_acyclic()

    return RegexProperty(
        alphabet=alphabet,
        regex=regex,
        symbol_to_label=symbol_to_label,
    )
