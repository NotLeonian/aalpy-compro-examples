from collections.abc import Callable, Hashable
from typing import Generic, TypeVar

from aalpy.base import SUL

Hashable_T = TypeVar("Hashable_T", bound=Hashable)


class PrefixAcceptingSUL(SUL, Generic[Hashable_T]):
    """
    愚直や CYK 法などで実装された
    accepts(word: tuple[T, ...]) -> bool
    を受け取る、AALpy の SUL のラッパー

    型の抽象化およびハッシュ化の都合により
    引数 word の型は str 等ではないことに注意
    """

    def __init__(self, accepts: Callable[[tuple[Hashable_T, ...]], bool]):
        super().__init__()
        self.accepts = accepts
        self.prefix: list[Hashable_T] = []
        self.memo: dict[tuple[Hashable_T, ...], bool] = {}

    def pre(self) -> None:
        self.prefix.clear()

    def post(self) -> None:
        pass

    def step(self, letter: Hashable_T | None) -> bool:
        if letter is not None:
            self.prefix.append(letter)

        key = tuple(self.prefix)
        if key in self.memo:
            return self.memo[key]

        val = self.accepts(key)
        self.memo[key] = val
        return val
