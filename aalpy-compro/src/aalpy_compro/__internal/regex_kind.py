from typing import Literal, TypeAlias

RegexKindLiteral: TypeAlias = Literal[
    "empty_set",
    "epsilon",
    "symbol",
    "concat",
    "union",
    "star",
]


def regex_kind_precedence(kind: RegexKindLiteral) -> int:
    if kind == "union":
        return 1
    if kind == "concat":
        return 2
    if kind == "star":
        return 3
    return 4


def parenthesize_text(*, text: str, inner_prec: int, outer_prec: int) -> str:
    if inner_prec < outer_prec:
        return f"({text})"
    return text
