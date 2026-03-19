from collections import deque
from collections.abc import Hashable, Sequence
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from aalpy.automata import Dfa

from .validate_aalpy_alphabet import validate_aalpy_alphabet
from .missing_symbol_payload import MissingSymbolPayload
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


def regex_to_nfa(regex: Regex[T]) -> Nfa[T]:
    """
    Thompson's construction
    """

    builder = NfaBuilder[T]()
    call_stack: deque[tuple[Regex[T], bool]] = deque([(regex, False)])
    fragment_stack: list[tuple[int, int]] = []

    while call_stack:
        node, ready = call_stack.pop()
        kind = node._kind

        if not ready:
            if kind == "empty_set":
                fragment_stack.append((builder.new_state(), builder.new_state()))
                continue

            if kind == "epsilon":
                start = builder.new_state()
                end = builder.new_state()
                builder.add_epsilon_transition(start, end)
                fragment_stack.append((start, end))
                continue

            if kind == "symbol":
                start = builder.new_state()
                end = builder.new_state()
                payload = node._symbol
                if isinstance(payload, MissingSymbolPayload):
                    raise AssertionError("Symbol regex must carry `_symbol`.")
                builder.add_symbol_transition(start, payload, end)
                fragment_stack.append((start, end))
                continue

            call_stack.append((node, True))
            for child in reversed(node._parts):
                call_stack.append((child, False))
            continue

        if kind == "concat":
            child_count = len(node._parts)
            child_fragments = fragment_stack[-child_count:]
            del fragment_stack[-child_count:]
            first_start, current_end = child_fragments[0]
            for next_start, next_end in child_fragments[1:]:
                builder.add_epsilon_transition(current_end, next_start)
                current_end = next_end
            fragment_stack.append((first_start, current_end))
            continue

        if kind == "union":
            child_count = len(node._parts)
            child_fragments = fragment_stack[-child_count:]
            del fragment_stack[-child_count:]
            start = builder.new_state()
            end = builder.new_state()
            for part_start, part_end in child_fragments:
                builder.add_epsilon_transition(start, part_start)
                builder.add_epsilon_transition(part_end, end)
            fragment_stack.append((start, end))
            continue

        if kind == "star":
            inner_start, inner_end = fragment_stack.pop()
            start = builder.new_state()
            end = builder.new_state()
            builder.add_epsilon_transition(start, end)
            builder.add_epsilon_transition(start, inner_start)
            builder.add_epsilon_transition(inner_end, end)
            builder.add_epsilon_transition(inner_end, inner_start)
            fragment_stack.append((start, end))
            continue

        raise AssertionError(f"Unknown regex kind: {kind!r}")

    if len(fragment_stack) != 1:
        raise AssertionError(
            "Internal error: Thompson construction did not end with exactly one fragment."
        )

    start, end = fragment_stack.pop()
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
    alphabet_tuple = validate_aalpy_alphabet(alphabet)

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
