from collections.abc import Hashable, Iterable
from dataclasses import dataclass
from typing import Generic, Literal, Self, TypeAlias, TypeVar

from .__internal.missing_symbol_payload import (
    MissingSymbolPayload,
    MISSING_SYMBOL_PAYLOAD,
)

Hashable_T = TypeVar("Hashable_T", bound=Hashable)

RegexKindLiteral: TypeAlias = Literal[
    "empty_set",
    "epsilon",
    "symbol",
    "concat",
    "union",
    "star",
]


@dataclass(frozen=True, slots=True)
class Regex(Generic[Hashable_T]):
    """
    正規表現を AST で表すオブジェクト。

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
        deduped = list(set(flat))
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

        regex: Self = cls.epsilon()
        for symbol in word:
            regex = regex.concat(cls.symbol(symbol))
        return regex

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

        visiting: set[int] = set()
        visited: set[int] = set()

        def dfs(node: Self) -> None:
            node_id = id(node)
            if node_id in visited:
                return
            if node_id in visiting:
                raise ValueError("Cyclic Regex is not supported.")

            visiting.add(node_id)
            for child in node._parts:
                dfs(child)
            visiting.remove(node_id)
            visited.add(node_id)

        dfs(self)

    def symbols(self) -> frozenset[Hashable_T]:
        """
        この正規表現 AST 内に実際に出現する文字の集合を
        frozenset で返す。
        """

        self.ensure_acyclic()

        result: set[Hashable_T] = set()
        visited: set[int] = set()

        def dfs(node: Self) -> None:
            node_id = id(node)
            if node_id in visited:
                return
            visited.add(node_id)

            if node._kind == "symbol":
                result.add(node.__require_symbol_payload())
                return

            for child in node._parts:
                dfs(child)

        dfs(self)
        return frozenset(result)

    def __to_string(self, *, outer_prec: int = 0) -> str:
        self.ensure_acyclic()

        if self._kind == "empty_set":
            return "∅"
        if self._kind == "epsilon":
            return "ε"
        if self._kind == "symbol":
            return repr(self.__require_symbol_payload())
        if self._kind == "concat":
            s = " ".join(
                part.__maybe_parenthesize(outer_prec=2) for part in self._parts
            )
            return f"({s})" if outer_prec > 2 else s
        if self._kind == "union":
            s = " | ".join(
                part.__maybe_parenthesize(outer_prec=1) for part in self._parts
            )
            return f"({s})" if outer_prec > 1 else s
        if self._kind == "star":
            child = self._parts[0]
            child_str = child.__to_string(outer_prec=3)
            if child._kind in ["concat", "union"]:
                child_str = f"({child_str})"
            return f"{child_str}*"

        raise AssertionError(f"Unknown regex kind: {self._kind!r}")

    def __maybe_parenthesize(self, *, outer_prec: int) -> str:
        inner_prec = 4
        if self._kind == "union":
            inner_prec = 1
        elif self._kind == "concat":
            inner_prec = 2
        elif self._kind == "star":
            inner_prec = 3

        text = self.__to_string(outer_prec=inner_prec)
        if inner_prec < outer_prec:
            return f"({text})"

        return text

    def __str__(self) -> str:
        return self.__to_string()


__all__ = [
    "Regex",
]
