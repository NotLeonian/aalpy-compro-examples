from collections.abc import Callable, Hashable
from typing import Generic, TypeVar, cast

from aalpy.base import SUL

T = TypeVar("T", bound=Hashable)
_NOT_EVALUATED = object()


class _PrefixCacheNode(Generic[T]):
    __slots__ = ("children", "output")

    def __init__(self) -> None:
        self.children: dict[T, _PrefixCacheNode[T]] | None = None
        self.output: object = _NOT_EVALUATED

    def child(self, letter: T) -> "_PrefixCacheNode[T]":
        children = self.children
        if children is None:
            children = self.children = {}
        node = children.get(letter)
        if node is None:
            node = children[letter] = _PrefixCacheNode()
        return node


class PrefixAcceptingSUL(SUL, Generic[T]):
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
        self._root = _PrefixCacheNode[T]()
        self._current: _PrefixCacheNode[T] | None = self._root

    def pre(self) -> None:
        self.prefix.clear()
        self._current = self._root

    def post(self) -> None:
        pass

    def step(self, letter: T | None) -> bool:
        if letter is not None:
            self.prefix.append(letter)

        node = self._current
        try:
            if node is None:
                # A failed lookup leaves the input in the prefix until pre().
                node = self._root
                for symbol in self.prefix:
                    node = node.child(symbol)
            elif letter is not None:
                # Keep cache hits on the hot path free of extra method calls.
                children = node.children
                child = children.get(letter) if children is not None else None
                node = child if child is not None else node.child(letter)
        except TypeError as e:
            self._current = None
            raise TypeError(
                "Input symbols must be hashable because prefix words are used "
                "as memoization keys in PrefixAcceptingSUL."
            ) from e

        self._current = node
        if node.output is _NOT_EVALUATED:
            # Copy the full prefix only when the callback needs to evaluate it.
            node.output = self.accepts(tuple(self.prefix))

        return cast(bool, node.output)
