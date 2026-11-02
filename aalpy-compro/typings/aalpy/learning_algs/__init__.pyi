"""DFA learning entry points used by aalpy-compro."""

from collections.abc import Sequence
from typing import Any, Literal, TypeAlias, overload

from aalpy.automata import Dfa
from aalpy.base import SUL, Oracle
from aalpy.base.Automaton import InputType

_KVCexProcessing: TypeAlias = Literal[
    "rs", "linear_fwd", "linear_bwd", "exponential_fwd", "exponential_bwd"
]
_LStarCexProcessing: TypeAlias = _KVCexProcessing | Literal["longest_prefix"] | None
_ClosingStrategy: TypeAlias = Literal["shortest_first", "longest_first", "single"]
_LearningData: TypeAlias = dict[str, Any]

@overload
def run_Lstar(
    alphabet: list[InputType],
    sul: SUL,
    eq_oracle: Oracle,
    automaton_type: Literal["dfa"],
    samples: list[tuple[Sequence[InputType], Sequence[bool]]] | None = None,
    closing_strategy: _ClosingStrategy = "shortest_first",
    cex_processing: _LStarCexProcessing = "rs",
    e_set_suffix_closed: bool = False,
    all_prefixes_in_obs_table: bool = True,
    max_learning_rounds: int | None = None,
    cache_and_non_det_check: bool = True,
    return_data: Literal[False] = False,
    print_level: int = 2,
) -> Dfa[InputType]: ...
@overload
def run_Lstar(
    alphabet: list[InputType],
    sul: SUL,
    eq_oracle: Oracle,
    automaton_type: Literal["dfa"],
    samples: list[tuple[Sequence[InputType], Sequence[bool]]] | None = None,
    closing_strategy: _ClosingStrategy = "shortest_first",
    cex_processing: _LStarCexProcessing = "rs",
    e_set_suffix_closed: bool = False,
    all_prefixes_in_obs_table: bool = True,
    max_learning_rounds: int | None = None,
    cache_and_non_det_check: bool = True,
    return_data: bool = False,
    print_level: int = 2,
) -> Dfa[InputType] | tuple[Dfa[InputType], _LearningData]: ...
@overload
def run_KV(
    alphabet: list[InputType],
    sul: SUL,
    eq_oracle: Oracle,
    automaton_type: Literal["dfa"],
    cex_processing: _KVCexProcessing = "rs",
    max_learning_rounds: int | None = None,
    cache_and_non_det_check: bool = True,
    return_data: Literal[False] = False,
    print_level: int = 2,
) -> Dfa[InputType]: ...
@overload
def run_KV(
    alphabet: list[InputType],
    sul: SUL,
    eq_oracle: Oracle,
    automaton_type: Literal["dfa"],
    cex_processing: _KVCexProcessing = "rs",
    max_learning_rounds: int | None = None,
    cache_and_non_det_check: bool = True,
    return_data: bool = False,
    print_level: int = 2,
) -> Dfa[InputType] | tuple[Dfa[InputType], _LearningData]: ...
