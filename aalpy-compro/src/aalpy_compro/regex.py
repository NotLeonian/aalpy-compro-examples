from collections import deque
from collections.abc import Hashable, Iterable
from dataclasses import dataclass
from typing import Generic, Self, TypeVar

from .__internal.regex_kind import (
    RegexKindLiteral,
    regex_kind_precedence,
    parenthesize_text,
)
from .__internal.missing_symbol_payload import (
    MissingSymbolPayload,
    MISSING_SYMBOL_PAYLOAD,
)

Hashable_T = TypeVar("Hashable_T", bound=Hashable)


@dataclass(frozen=True, slots=True)
class Regex(Generic[Hashable_T]):
    """
    正規表現を AST で表すオブジェクト。

    `Regex` の等値性・ハッシュは、この AST の構造に基づく。
    つまり、このクラスは正規言語の同値類の canonical representative ではなく、
    あくまで正規表現 AST の値オブジェクトである。
    したがって、局所的な簡約 (例: `ε` の除去、`∅` の吸収、`(R*)* -> R*`,
    `R | R -> R`) は行うが、一般の言語同値までは同一視しない。
    特に、和集合の子要素順は保持されるため、`a | b` と `b | a` は、
    同じ言語を表していても別の AST として比較されうる。

    公開 API からは有限木しか構築できないが、
    悪意のあるコードが循環参照を作ることはできる。
    防御には `ensure_acyclic()` を用いる。
    """

    _kind: RegexKindLiteral
    _symbol: Hashable_T | MissingSymbolPayload = MISSING_SYMBOL_PAYLOAD
    _parts: tuple[Self, ...] = ()

    def __post_init__(self) -> None:
        if self._kind == "empty_set" or self._kind == "epsilon":
            if not isinstance(self._symbol, MissingSymbolPayload) or self._parts:
                raise ValueError(f"Regex kind {self._kind!r} cannot have payload.")
            return

        if self._kind == "symbol":
            if isinstance(self._symbol, MissingSymbolPayload):
                raise ValueError("Symbol regex requires `_symbol`.")
            try:
                hash(self._symbol)
            except TypeError as e:
                raise TypeError("Symbol regex requires a hashable `_symbol`.") from e
            if self._parts:
                raise ValueError("Symbol regex cannot have child regexes.")
            return

        if self._kind == "concat" or self._kind == "union":
            if not isinstance(self._symbol, MissingSymbolPayload):
                raise ValueError(f"Regex kind {self._kind!r} cannot have `_symbol`.")
            if len(self._parts) < 2:
                raise ValueError(
                    f"Regex kind {self._kind!r} requires at least two child regexes."
                )
            return

        if self._kind == "star":
            if not isinstance(self._symbol, MissingSymbolPayload):
                raise ValueError("Star regex cannot have `_symbol`.")
            if len(self._parts) != 1:
                raise ValueError("Star regex requires exactly one child regex.")
            return

        raise ValueError(f"Unknown regex kind: {self._kind!r}.")

    @classmethod
    def empty_set(cls) -> Self:
        """
        空集合（空言語）
        """

        return cls("empty_set")

    @classmethod
    def epsilon(cls) -> Self:
        """
        空文字列言語ε
        """

        return cls("epsilon")

    @classmethod
    def symbol(cls, symbol: Hashable_T) -> Self:
        """
        symbol のみを含む単集合言語
        """

        return cls("symbol", _symbol=symbol)

    @classmethod
    def __concat(cls, *parts: Self) -> Self:
        flat: list[Self] = []
        for part in parts:
            if part._kind == "empty_set":
                return cls.empty_set()  # 空言語との連結は空言語になる
            if part._kind == "epsilon":
                continue  # 連結ではεは無視してよい
            if part._kind == "concat":
                flat.extend(part._parts)
            else:
                flat.append(part)

        if not flat:
            return cls.epsilon()  # flat に何も入っていない場合はεになる
        if len(flat) == 1:
            return flat[0]
        return cls("concat", _parts=tuple(flat))

    @classmethod
    def __union(cls, *parts: Self) -> Self:
        flat: list[Self] = []
        for part in parts:
            if part._kind == "empty_set":
                continue  # 和集合では空言語は無視してよい
            if part._kind == "union":
                flat.extend(part._parts)
            else:
                flat.append(part)

        if not flat:
            return cls.empty_set()
        deduped = list(dict.fromkeys(flat))
        if len(deduped) == 1:
            return deduped[0]
        return cls("union", _parts=tuple(deduped))

    def concat(self, *others: Self) -> Self:
        """
        連結
        """

        return self.__concat(self, *others)

    def union(self, *others: Self) -> Self:
        """
        和集合
        """

        return self.__union(self, *others)

    @classmethod
    def word(cls, word: Iterable[Hashable_T]) -> Self:
        """
        語 word のみを含む単集合言語
        """

        parts = tuple(cls.symbol(symbol) for symbol in word)
        return cls.__concat(*parts)

    def star(self) -> Self:
        """
        クリーネ閉包 `*`
        """

        if self._kind == "empty_set" or self._kind == "epsilon":
            return self.epsilon()
        if self._kind == "star":
            return self
        return type(self)("star", _parts=(self,))

    def plus(self) -> Self:
        """
        正規表現の `+` にあたる。
        """

        return self.concat(self.star())

    def optional(self) -> Self:
        """
        正規表現の `?` にあたる。
        """

        return self.union(self.epsilon())

    def __add__(self, other: Self) -> Self:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.concat(other)

    def __or__(self, other: Self) -> Self:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.union(other)

    def __require_symbol_payload(self) -> Hashable_T:
        if self._kind != "symbol":
            raise ValueError("This regex node does not carry a symbol payload.")
        payload = self._symbol
        if isinstance(payload, MissingSymbolPayload):
            raise AssertionError("Symbol regex must carry `_symbol`.")
        return payload

    def ensure_acyclic(self) -> None:
        """
        このインスタンスが循環参照になっていないことを保証する。

        循環参照になっていれば ValueError が返る。
        """

        visited: set[int] = set()
        visiting: set[int] = {id(self)}
        stack: deque[tuple[Regex[Hashable_T], int]] = deque([(self, 0)])

        while stack:
            node, child_index = stack[-1]
            if child_index >= len(node._parts):
                stack.pop()
                node_id = id(node)
                visiting.discard(node_id)
                visited.add(node_id)
                continue

            child = node._parts[child_index]
            stack[-1] = (node, child_index + 1)

            child_id = id(child)
            if child_id in visited:
                continue
            if child_id in visiting:
                raise ValueError("Cyclic Regex is not supported.")

            visiting.add(child_id)
            stack.append((child, 0))

    def symbols(self) -> frozenset[Hashable_T]:
        """
        この正規表現 AST 内に実際に出現する文字の集合を
        frozenset で返す。
        """

        self.ensure_acyclic()

        result: set[Hashable_T] = set()
        visited: set[int] = set()
        stack: deque[Regex[Hashable_T]] = deque([self])

        while stack:
            node = stack.pop()
            node_id = id(node)
            if node_id in visited:
                continue
            visited.add(node_id)

            if node._kind == "symbol":
                result.add(node.__require_symbol_payload())
                continue

            for child in reversed(node._parts):
                stack.append(child)

        return frozenset(result)

    def __to_string(self, *, outer_prec: int = 0) -> str:
        self.ensure_acyclic()

        texts: dict[int, str] = {}
        stack: list[tuple[Regex[Hashable_T], int]] = [(self, 0)]

        while stack:
            node, child_index = stack[-1]
            node_id = id(node)

            if node_id in texts:
                stack.pop()
                continue

            if child_index < len(node._parts):
                child = node._parts[child_index]
                stack[-1] = (node, child_index + 1)
                child_id = id(child)
                if child_id not in texts:
                    stack.append((child, 0))
                continue

            kind = node._kind
            if kind == "empty_set":
                text = "∅"
            elif kind == "epsilon":
                text = "ε"
            elif kind == "symbol":
                text = repr(node.__require_symbol_payload())
            elif kind == "concat":
                text = " ".join(
                    parenthesize_text(
                        text=texts[id(part)],
                        inner_prec=regex_kind_precedence(part._kind),
                        outer_prec=2,
                    )
                    for part in node._parts
                )
            elif kind == "union":
                text = " | ".join(
                    parenthesize_text(
                        text=texts[id(part)],
                        inner_prec=regex_kind_precedence(part._kind),
                        outer_prec=1,
                    )
                    for part in node._parts
                )
            elif kind == "star":
                child = node._parts[0]
                child_text = parenthesize_text(
                    text=texts[id(child)],
                    inner_prec=regex_kind_precedence(child._kind),
                    outer_prec=3,
                    parenthesize_on_equal=(child._kind == "star"),
                )
                text = f"{child_text}*"
            else:
                raise AssertionError(f"Unknown regex kind: {kind!r}")

            texts[node_id] = text
            stack.pop()

        text = texts[id(self)]
        return parenthesize_text(
            text=text,
            inner_prec=regex_kind_precedence(self._kind),
            outer_prec=outer_prec,
        )

    def __str__(self) -> str:
        return self.__to_string()


__all__ = [
    "Regex",
]
