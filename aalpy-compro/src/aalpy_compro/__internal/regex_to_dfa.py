from collections import deque
from collections.abc import Hashable, Sequence
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from aalpy.automata import Dfa

from ..regex import Regex

T = TypeVar("T", bound=Hashable)


@dataclass
class NfaBuilder(Generic[T]):
    """
    正規表現から NFA を生成するためのビルダー
    """

    symbol_transitions: dict[int, dict[T, set[int]]] = field(default_factory=dict)
    epsilon_transitions: dict[int, set[int]] = field(default_factory=dict)
    _next_state_id: int = 0

    def new_state(self) -> int:
        state_id = self._next_state_id
        self._next_state_id += 1
        self.symbol_transitions.setdefault(state_id, {})
        self.epsilon_transitions.setdefault(state_id, set())
        return state_id

    def add_symbol_transition(self, src: int, symbol: T, dst: int) -> None:
        self.symbol_transitions.setdefault(src, {}).setdefault(symbol, set()).add(dst)
        self.symbol_transitions.setdefault(dst, {})
        self.epsilon_transitions.setdefault(src, set())
        self.epsilon_transitions.setdefault(dst, set())

    def add_epsilon_transition(self, src: int, dst: int) -> None:
        self.epsilon_transitions.setdefault(src, set()).add(dst)
        self.symbol_transitions.setdefault(src, {})
        self.symbol_transitions.setdefault(dst, {})
        self.epsilon_transitions.setdefault(dst, set())


@dataclass(frozen=True)
class Nfa(Generic[T]):
    """
    NFA を表現するクラス
    """

    start_state: int
    accepting_states: frozenset[int]
    symbol_transitions: dict[int, dict[T, set[int]]]
    epsilon_transitions: dict[int, set[int]]


def validate_alphabet(alphabet: Sequence[T]) -> tuple[T, ...]:
    alphabet_tuple = tuple(alphabet)

    try:
        alphabet_set = set(alphabet_tuple)
    except TypeError as e:
        raise ValueError("`alphabet` must contain only hashable symbols.") from e

    if len(alphabet_set) != len(alphabet_tuple):
        raise ValueError("`alphabet` must not contain duplicates.")

    return alphabet_tuple


def build_fragment(
    regex: Regex[T],
    builder: NfaBuilder[T],
) -> tuple[int, int]:
    if regex._kind == "empty_set":
        return builder.new_state(), builder.new_state()

    if regex._kind == "epsilon":
        start = builder.new_state()
        end = builder.new_state()
        builder.add_epsilon_transition(start, end)
        return start, end

    if regex._kind == "symbol":
        start = builder.new_state()
        end = builder.new_state()
        builder.add_symbol_transition(start, regex.require_symbol_payload(), end)
        return start, end

    if regex._kind == "concat":
        parts = regex._parts
        first_start, current_end = build_fragment(parts[0], builder)
        for part in parts[1:]:
            next_start, next_end = build_fragment(part, builder)
            builder.add_epsilon_transition(current_end, next_start)
            current_end = next_end
        return first_start, current_end

    if regex._kind == "union":
        start = builder.new_state()
        end = builder.new_state()
        for part in regex._parts:
            part_start, part_end = build_fragment(part, builder)
            builder.add_epsilon_transition(start, part_start)
            builder.add_epsilon_transition(part_end, end)
        return start, end

    if regex._kind == "star":
        start = builder.new_state()
        end = builder.new_state()
        inner_start, inner_end = build_fragment(regex._parts[0], builder)
        builder.add_epsilon_transition(start, end)
        builder.add_epsilon_transition(start, inner_start)
        builder.add_epsilon_transition(inner_end, end)
        builder.add_epsilon_transition(inner_end, inner_start)
        return start, end

    raise AssertionError(f"Unknown regex kind: {regex._kind!r}")


def regex_to_nfa(regex: Regex[T]) -> Nfa[T]:
    builder = NfaBuilder[T]()
    start, end = build_fragment(regex, builder)
    return Nfa(
        start_state=start,
        accepting_states=frozenset({end}),
        symbol_transitions=builder.symbol_transitions,
        epsilon_transitions=builder.epsilon_transitions,
    )


def epsilon_closure(
    nfa: Nfa[T],
    states: frozenset[int],
    *,
    cache: dict[frozenset[int], frozenset[int]],
) -> frozenset[int]:
    cached = cache.get(states)
    if cached is not None:
        return cached

    closure = set(states)
    stack = deque(states)

    while stack:
        state = stack.pop()
        for next_state in nfa.epsilon_transitions.get(state, ()):
            if next_state in closure:
                continue
            closure.add(next_state)
            stack.append(next_state)

    frozen = frozenset(closure)
    cache[states] = frozen
    return frozen


def move(nfa: Nfa[T], states: frozenset[int], symbol: T) -> frozenset[int]:
    reached: set[int] = set()
    for state in states:
        reached.update(nfa.symbol_transitions.get(state, {}).get(symbol, ()))
    return frozenset(reached)


def determinize_complete_state_setup(
    nfa: Nfa[T],
    *,
    alphabet: tuple[T, ...],
) -> dict[str, tuple[bool, dict[T, str]]]:
    closure_cache: dict[frozenset[int], frozenset[int]] = {}

    start_subset = epsilon_closure(
        nfa,
        frozenset({nfa.start_state}),
        cache=closure_cache,
    )

    subset_to_name: dict[frozenset[int], str] = {start_subset: "q0"}
    queue: deque[frozenset[int]] = deque([start_subset])
    state_setup: dict[str, tuple[bool, dict[T, str]]] = {}

    while queue:
        subset = queue.popleft()
        state_name = subset_to_name[subset]
        transitions: dict[T, str] = {}

        for symbol in alphabet:
            moved = move(nfa, subset, symbol)
            target_subset = epsilon_closure(nfa, moved, cache=closure_cache)
            if target_subset not in subset_to_name:
                subset_to_name[target_subset] = f"q{len(subset_to_name)}"
                queue.append(target_subset)
            transitions[symbol] = subset_to_name[target_subset]

        state_setup[state_name] = (
            any(state in nfa.accepting_states for state in subset),
            transitions,
        )

    return state_setup


def regex_to_dfa(
    *,
    regex: Regex[T],
    alphabet: Sequence[T],
) -> Dfa[T]:
    alphabet_tuple = validate_alphabet(alphabet)

    regex.ensure_acyclic()
    used_symbols = regex.symbols()
    missing_symbols = used_symbols.difference(alphabet_tuple)
    if missing_symbols:
        raise ValueError(
            "`regex` contains symbols that are not in `alphabet`: "
            f"{sorted(repr(symbol) for symbol in missing_symbols)}"
        )

    nfa = regex_to_nfa(regex)
    state_setup = determinize_complete_state_setup(nfa, alphabet=alphabet_tuple)
    dfa = Dfa.from_state_setup(state_setup)
    dfa.minimize()
    return dfa
