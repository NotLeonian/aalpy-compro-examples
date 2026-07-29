from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from typing import Any, Generic, TypeVar

from ._typevars import _InputType as InputType
from ._typevars import _OutputType as OutputType

# AALpy's automata modules import InputType and OutputType from this module.
__all__ = [
    "Automaton",
    "AutomatonState",
    "DeterministicAutomaton",
    "InputType",
    "OutputType",
]

class AutomatonState(ABC):
    state_id: Any
    transitions: Any
    prefix: tuple[Any, ...] | None

    def __init__(self, state_id: Any) -> None: ...
    def get_diff_state_transitions(self) -> list[Any]: ...
    def get_same_state_transitions(self) -> list[Any]: ...

_AutomatonStateType = TypeVar("_AutomatonStateType", bound=AutomatonState)

class Automaton(ABC, Generic[_AutomatonStateType]):
    initial_state: _AutomatonStateType
    states: list[_AutomatonStateType]
    characterization_set: list[Any]
    current_state: _AutomatonStateType

    def __init__(
        self,
        initial_state: _AutomatonStateType,
        states: list[_AutomatonStateType],
    ) -> None: ...
    @property
    def size(self) -> int: ...
    def reset_to_initial(self) -> None: ...
    @abstractmethod
    def step(self, letter: Any) -> Any: ...
    def is_input_complete(self) -> bool: ...
    def get_input_alphabet(self) -> list[Any]: ...
    def get_state_by_id(self, state_id: Any) -> _AutomatonStateType | None: ...
    def make_input_complete(
        self,
        missing_transition_go_to: str = "self_loop",
    ) -> None: ...
    def execute_sequence(
        self,
        origin_state: _AutomatonStateType,
        seq: Iterable[Any],
    ) -> list[Any]: ...
    def save(
        self,
        file_path: str = "LearnedModel",
        file_type: str = "dot",
    ) -> None: ...
    def visualize(
        self,
        path: str = "LearnedModel",
        file_type: str = "pdf",
        display_same_state_transitions: bool = True,
    ) -> None: ...
    @staticmethod
    @abstractmethod
    def from_state_setup(
        state_setup: dict[Any, Any],
        **kwargs: Any,
    ) -> Automaton: ...
    @abstractmethod
    def to_state_setup(self) -> dict[Any, Any]: ...
    def copy(self) -> Automaton[_AutomatonStateType]: ...
    def __reduce__(self) -> tuple[Any, tuple[dict[Any, Any]]]: ...

class DeterministicAutomaton(Automaton[_AutomatonStateType]):
    @abstractmethod
    def step(self, letter: Any) -> Any: ...
    def get_shortest_path(
        self,
        origin_state: _AutomatonStateType,
        target_state: _AutomatonStateType,
    ) -> tuple[Any, ...] | None: ...
    def is_strongly_connected(self) -> bool: ...
    def output_step(
        self,
        state: _AutomatonStateType,
        letter: Any,
    ) -> Any: ...
    def find_distinguishing_seq(
        self,
        state1: _AutomatonStateType,
        state2: _AutomatonStateType,
        alphabet: Iterable[Any],
    ) -> list[Any] | None: ...
    def compute_output_seq(
        self,
        state: _AutomatonStateType,
        sequence: Sequence[Any],
    ) -> list[Any]: ...
    def is_minimal(self) -> bool: ...
    def compute_characterization_set(
        self,
        char_set_init: Any = ...,
        online_suffix_closure: bool = ...,
        split_all_blocks: bool = ...,
        return_same_states: bool = ...,
        raise_warning: bool = ...,
    ) -> Any: ...
    def _split_blocks(
        self,
        blocks: list[list[_AutomatonStateType]],
        seq: Sequence[Any],
    ) -> list[list[_AutomatonStateType]]: ...
    def compute_prefixes(self) -> None: ...
    def minimize(self) -> None: ...
    def __eq__(self, other: object) -> bool: ...
