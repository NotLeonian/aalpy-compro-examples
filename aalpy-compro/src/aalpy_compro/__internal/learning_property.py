from collections.abc import Callable, Hashable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from importlib.util import spec_from_file_location, module_from_spec
from typing import Generic, TypeAlias, TypeVar, cast

T = TypeVar("T", bound=Hashable)

WordFactory: TypeAlias = Callable[[], Iterable[tuple[T, ...]]]


def require_hashable(value: Hashable, *, obj_name: str) -> None:
    try:
        hash(value)
    except TypeError as e:
        raise TypeError(f"{obj_name} must be hashable.") from e


def validate_alphabet(alphabet: Hashable, *, path: str) -> None:
    if not isinstance(alphabet, Sequence) or isinstance(alphabet, (str, bytes)):
        raise ValueError(f"`alphabet` must be a non-string sequence in {path}.")

    for i, symbol in enumerate(alphabet):
        require_hashable(
            symbol,
            obj_name=f"`alphabet[{i}]` in {path}",
        )


def iter_words(
    raw: Iterable[Iterable[T]],
    *,
    attr_name: str,
) -> Iterator[tuple[T, ...]]:
    if isinstance(raw, (str, bytes)):
        raise ValueError(
            f"`{attr_name}` must be a non-string iterable of non-string iterables."
        )

    for word_index, word in enumerate(raw):
        if isinstance(word, (str, bytes)):
            raise ValueError(
                f"`{attr_name}` must be a non-string iterable of non-string iterables."
            )
        try:
            tup = tuple(word)
        except TypeError as e:
            raise ValueError(
                f"`{attr_name}` must be a non-string iterable of non-string iterables."
            ) from e

        try:
            hash(tup)
        except TypeError as e:
            raise TypeError(
                f"`{attr_name}` contains a word at index {word_index} "
                "whose symbols must all be hashable."
            ) from e

        yield tup


def load_word_factory(
    mod: T,
    *,
    words_attr: str,
    iter_words_attr: str,
) -> WordFactory[T] | None:
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
            raw_words: Iterable[Iterable[T]] = raw,
            attr_name: str = words_attr,
        ) -> Iterable[tuple[T, ...]]:
            return iter_words(raw_words, attr_name=attr_name)

        return factory_with_words

    if has_iter_words:
        fn = getattr(mod, iter_words_attr)
        if not callable(fn):
            raise ValueError(f"`{iter_words_attr}` must be callable.")

        iter_words_fn = cast(Callable[[], Iterable[Iterable[T]]], fn)

        def factory_with_iter_words() -> Iterable[tuple[T, ...]]:
            produced = iter_words_fn()
            if not isinstance(produced, Iterable) or isinstance(produced, (str, bytes)):
                raise ValueError(
                    f"`{iter_words_attr}()` must return a non-string iterable of non-string iterables."
                )
            return iter_words(produced, attr_name=f"{iter_words_attr}()")

        return factory_with_iter_words

    return None


@dataclass(frozen=True)
class LearningProperty(Generic[T]):
    alphabet: Sequence[T]
    accepts: Callable[[tuple[T, ...]], bool]
    symbol_to_label: Callable[[T], str] = str
    fixed_eq_word_factory: WordFactory[T] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.alphabet, Sequence) or isinstance(
            self.alphabet, (str, bytes)
        ):
            raise ValueError("`alphabet` must be a non-string sequence.")

        for i, symbol in enumerate(self.alphabet):
            require_hashable(symbol, obj_name=f"`alphabet[{i}]`")

        if not callable(self.accepts):
            raise ValueError("`accepts` must be callable.")

        if not callable(self.symbol_to_label):
            raise ValueError("`symbol_to_label` must be callable.")

        if self.fixed_eq_word_factory is not None and not callable(
            self.fixed_eq_word_factory
        ):
            raise ValueError("`fixed_eq_word_factory` must be callable if provided.")


def load_learning_property(path: str) -> LearningProperty[Hashable]:
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
    raw_accepts = getattr(mod, "accepts")
    raw_symbol_to_label = getattr(mod, "symbol_to_label", str)

    if not callable(raw_accepts):
        raise ValueError(f"`accepts` must be callable in {path}.")
    if not callable(raw_symbol_to_label):
        raise ValueError(f"`symbol_to_label` must be callable in {path}.")

    accepts = cast(Callable[[tuple[Hashable, ...]], bool], raw_accepts)
    symbol_to_label = cast(Callable[[Hashable], str], raw_symbol_to_label)

    validate_alphabet(alphabet, path=path)

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
