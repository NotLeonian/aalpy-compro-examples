from collections.abc import Callable, Hashable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from importlib.util import spec_from_file_location, module_from_spec
from typing import Generic, TypeAlias, TypeVar, cast

Hashable_T = TypeVar("Hashable_T", bound=Hashable)

WordFactory: TypeAlias = Callable[[], Iterable[tuple[Hashable_T, ...]]]


def iter_words(
    raw: Iterable[Iterable[Hashable_T]],
    *,
    attr_name: str,
) -> Iterator[tuple[Hashable_T, ...]]:
    if isinstance(raw, (str, bytes)):
        raise ValueError(
            f"`{attr_name}` must be a non-string iterable of non-string iterables."
        )

    for word in raw:
        if isinstance(word, (str, bytes)):
            raise ValueError(
                f"`{attr_name}` must be a non-string iterable of non-string iterables."
            )
        try:
            yield tuple(word)
        except TypeError as e:
            raise ValueError(
                f"`{attr_name}` must be a non-string iterable of non-string iterables."
            ) from e


def load_word_factory(
    mod: object,
    *,
    words_attr: str,
    iter_words_attr: str,
) -> WordFactory[object] | None:
    has_words = hasattr(mod, words_attr)
    has_iter_words = hasattr(mod, iter_words_attr)

    if has_words and has_iter_words:
        raise ValueError(
            f"Define at most one of `{words_attr}` and `{iter_words_attr}`."
        )

    if has_words:
        raw = getattr(mod, words_attr)

        if isinstance(raw, Iterator):
            raise ValueError(
                f"`{words_attr}` must be re-iterable. Use `{iter_words_attr}` for generators."
            )
        if not isinstance(raw, Iterable) or isinstance(raw, (str, bytes)):
            raise ValueError(
                f"`{words_attr}` must be a non-string iterable of non-string iterables."
            )

        def factory_with_words(
            raw_words: Iterable[Iterable[object]] = raw,
            attr_name: str = words_attr,
        ) -> Iterable[tuple[object, ...]]:
            return iter_words(raw_words, attr_name=attr_name)

        return factory_with_words

    if has_iter_words:
        fn = getattr(mod, iter_words_attr)
        if not callable(fn):
            raise ValueError(f"`{iter_words_attr}` must be callable.")

        iter_words_fn = cast(Callable[[], Iterable[Iterable[object]]], fn)

        def factory_with_iter_words() -> Iterable[tuple[object, ...]]:
            produced = iter_words_fn()
            if not isinstance(produced, Iterable) or isinstance(produced, (str, bytes)):
                raise ValueError(
                    f"`{iter_words_attr}()` must return a non-string iterable of non-string iterables."
                )
            return iter_words(produced, attr_name=f"{iter_words_attr}()")

        return factory_with_iter_words

    return None


@dataclass(frozen=True)
class LearningProperty(Generic[Hashable_T]):
    alphabet: Sequence[Hashable_T]
    accepts: Callable[[tuple[Hashable_T, ...]], bool]
    symbol_to_label: Callable[[Hashable_T], str] = str
    fixed_eq_word_factory: WordFactory[Hashable_T] | None = None


def load_property(path: str) -> LearningProperty[object]:
    """
    必須:
      - alphabet: Sequence[T]
      - accepts: Callable[[tuple[T, ...]], bool]

    任意:
      - symbol_to_label: Callable[[T], str]
      - eq_words: re-iterable Iterable[Iterable[T]]
      - iter_eq_words: Callable[[], Iterable[Iterable[T]]]

    備考:
      - `eq_words` と `iter_eq_words` は同時に定義できない。
      - 大きい word 集合は `iter_eq_words` を使う。
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
    fixed_eq_word_factory = load_word_factory(
        mod,
        words_attr="eq_words",
        iter_words_attr="iter_eq_words",
    )

    return LearningProperty(
        alphabet=alphabet,
        accepts=accepts,
        symbol_to_label=symbol_to_label,
        fixed_eq_word_factory=fixed_eq_word_factory,
    )


CustomEqOracleFactoryAttrs: list[str] = ["fixed_eq_word_factory"]
