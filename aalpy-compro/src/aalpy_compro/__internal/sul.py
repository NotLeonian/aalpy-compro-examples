from collections.abc import Callable

from aalpy.base import SUL


class PrefixAcceptingSUL[T](SUL):
    """
    愚直や CYK 法などで実装された
    accepts(word: tuple[T, ...]) -> bool
    を受け取る、AALpy の SUL のラッパー

    型の抽象化およびハッシュ化の都合により
    引数 word の型は str 等ではないことに注意
    """

    def __init__(self, accepts: Callable[[tuple[T, ...]], bool]):
        super().__init__()
        self.accepts = accepts
        self.prefix: list[T] = []
        self.memo: dict[tuple[T, ...], bool] = {}

    def pre(self) -> None:
        self.prefix.clear()

    def post(self) -> None:
        pass

    def step(self, letter: T | None) -> bool:
        if letter is not None:
            self.prefix.append(letter)

        key = tuple(self.prefix)
        if key in self.memo:
            return self.memo[key]

        val = self.accepts(key)
        self.memo[key] = val
        return val
