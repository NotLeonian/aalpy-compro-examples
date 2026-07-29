from typing import TypeVar

_InputType = TypeVar("_InputType")
_OutputType = TypeVar("_OutputType")

# These are re-exported under AALpy's public names by Automaton.pyi.
__all__ = ["_InputType", "_OutputType"]
