from collections.abc import Sequence
from typing import Any, Generic

from aalpy.base import AutomatonState, DeterministicAutomaton
from aalpy.base.Automaton import InputType

class DfaState(AutomatonState, Generic[InputType]):
    transitions: dict[InputType, DfaState[InputType]]
    prefix: tuple[InputType, ...] | None
    is_accepting: bool

    def __init__(self, state_id: Any, is_accepting: bool = False) -> None: ...
    @property
    def output(self) -> bool: ...

class Dfa(DeterministicAutomaton[DfaState[InputType]]):
    def __init__(
        self,
        initial_state: DfaState[InputType],
        states: list[DfaState[InputType]],
    ) -> None: ...
    def step(self, letter: InputType | None) -> bool: ...
    def get_input_alphabet(self) -> list[InputType]: ...
    def compute_output_seq(
        self,
        state: DfaState[InputType],
        sequence: Sequence[InputType],
    ) -> list[bool]: ...
    def to_state_setup(self) -> dict[Any, tuple[bool, dict[InputType, Any]]]: ...
    @staticmethod
    def from_state_setup(
        state_setup: dict[Any, tuple[bool, dict[InputType, Any]]],
        **kwargs: Any,
    ) -> Dfa[InputType]: ...
