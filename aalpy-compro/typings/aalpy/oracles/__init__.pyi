"""Equivalence oracles used by aalpy-compro."""

from typing import Any

from aalpy.base import SUL, DeterministicAutomaton, Oracle

class WpMethodEqOracle(Oracle):
    m: int

    def __init__(
        self,
        alphabet: list[Any],
        sul: SUL,
        max_number_of_states: int = 4,
    ) -> None: ...
    def find_cex(
        self,
        hypothesis: DeterministicAutomaton[Any],
    ) -> tuple[Any, ...] | None: ...

class RandomWpMethodEqOracle(Oracle):
    min_length: int
    expected_length: int
    bound: int

    def __init__(
        self,
        alphabet: list[Any],
        sul: SUL,
        min_length: int = 1,
        expected_length: int = 10,
        num_tests: int = 1000,
    ) -> None: ...
    def find_cex(
        self,
        hypothesis: DeterministicAutomaton[Any],
    ) -> tuple[Any, ...] | None: ...

class StatePrefixEqOracle(Oracle):
    walks_per_state: int
    steps_per_walk: int
    max_tests: int | None
    depth_first: bool

    def __init__(
        self,
        alphabet: list[Any],
        sul: SUL,
        walks_per_state: int = 25,
        walk_len: int = 12,
        max_tests: int | None = None,
        depth_first: bool = True,
    ) -> None: ...
    def find_cex(
        self,
        hypothesis: DeterministicAutomaton[Any],
    ) -> tuple[Any, ...] | None: ...
