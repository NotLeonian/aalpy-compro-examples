from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from typing import Generic, TypeVar, cast

from .normalize_alphabet import normalize_alphabet
from ..regex import Regex

T = TypeVar("T", bound=Hashable)


@dataclass(frozen=True)
class RegexProperty(Generic[T]):
    alphabet: Sequence[T]
    regex: Regex[T]
    symbol_to_label: Callable[[T], str] = str


def load_regex_property(path: str) -> RegexProperty[Hashable]:
    """
    必須:
      - alphabet: Sequence[T]
      - regex: Regex[T]

    任意:
      - symbol_to_label: Callable[[T], str]
    """

    spec = spec_from_file_location("regex_property", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load property from {path}.")

    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)

    if not hasattr(mod, "alphabet"):
        raise ValueError(f"`alphabet` must be defined in {path}.")
    if not hasattr(mod, "regex"):
        raise ValueError(f"`regex` must be defined in {path}.")

    raw_alphabet = getattr(mod, "alphabet")
    regex = getattr(mod, "regex")
    raw_symbol_to_label = getattr(mod, "symbol_to_label", str)

    if not isinstance(regex, Regex):
        raise ValueError(
            f"`regex` must be an instance of `aalpy_compro.regex.Regex` in {path}."
        )
    if not callable(raw_symbol_to_label):
        raise ValueError(f"`symbol_to_label` must be callable in {path}.")

    alphabet = normalize_alphabet(raw_alphabet, path=path)
    symbol_to_label = cast(Callable[[Hashable], str], raw_symbol_to_label)

    regex.ensure_acyclic()

    return RegexProperty(
        alphabet=alphabet,
        regex=regex,
        symbol_to_label=symbol_to_label,
    )
