from collections.abc import Callable, Sequence
from dataclasses import dataclass
from importlib.util import spec_from_file_location, module_from_spec
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class LearningProperty(Generic[T]):
    alphabet: Sequence[T]
    accepts: Callable[[tuple[T, ...]], bool]
    symbol_to_label: Callable[[T], str] = str


def load_property(path: str) -> LearningProperty[object]:
    """
    必須:
      - alphabet: Sequence[T]
      - accepts: Callable[[tuple[T, ...]], bool]

    任意:
      - symbol_to_label: Callable[[T], str] (デフォルトは str)
    """

    spec = spec_from_file_location("learning_property", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load property from {path}.")

    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)

    if not hasattr(mod, "alphabet"):
        raise ValueError(f"`alphabet` must be defined in {path}.")
    if not hasattr(mod, "accepts"):
        raise ValueError(f"`accepts` must be defined in {path}.")

    alphabet = getattr(mod, "alphabet")
    accepts = getattr(mod, "accepts")
    symbol_to_label = getattr(mod, "symbol_to_label", str)

    return LearningProperty(alphabet, accepts, symbol_to_label)
