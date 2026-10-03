from collections import deque
from collections.abc import Hashable, Sequence
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from aalpy.automata import Dfa

from ..regex import ComplementRegex, Regex
from .minimize_dfa import minimize_complete_dfa
from .missing_symbol_payload import MissingSymbolPayload
from .validation_for_aalpy import validate_aalpy_alphabet

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


def regex_to_nfa(
    *,
    regex: Regex[T],
    alphabet: Sequence[T],
) -> Nfa[T]:
    """
    Thompson’s construction

    `Regex.dot()` は、引数 alphabet 上の 1 文字全体として展開される。
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

            if kind == "dot":
                start = builder.new_state()
                end = builder.new_state()
                for symbol in alphabet:
                    builder.add_symbol_transition(start, symbol, end)
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


def determinize_complete_state_setup(
    nfa: Nfa[T],
    *,
    alphabet: tuple[T, ...],
) -> dict[str, tuple[bool, dict[T, str]]]:
    # Only these states can consume input or decide acceptance after epsilon closure.
    active_states = nfa.accepting_states.union(
        state for state, transitions in nfa.symbol_transitions.items() if transitions
    )
    closure_cache: dict[frozenset[int], frozenset[int]] = {}
    alphabet_set = set(alphabet)

    def epsilon_closure(seeds: frozenset[int]) -> frozenset[int]:
        cached = closure_cache.get(seeds)
        if cached is not None:
            return cached

        visited = set(seeds)
        stack = list(seeds)
        reached: set[int] = set()
        while stack:
            state = stack.pop()
            if state in active_states:
                reached.add(state)
            for target in nfa.epsilon_transitions.get(state, ()):
                if target not in visited:
                    visited.add(target)
                    stack.append(target)

        result = frozenset(reached)
        closure_cache[seeds] = result
        return result

    start_subset = epsilon_closure(frozenset({nfa.start_state}))
    subset_to_name: dict[frozenset[int], str] = {start_subset: "q0"}
    queue = deque([start_subset])
    state_setup: dict[str, tuple[bool, dict[T, str]]] = {}

    while queue:
        subset = queue.popleft()
        targets: dict[T, set[int]] = {}
        # Sparse transitions avoid revisiting every state for every alphabet symbol.
        for state in subset:
            for symbol, destinations in nfa.symbol_transitions.get(state, {}).items():
                if symbol not in alphabet_set:
                    continue
                reached = targets.get(symbol)
                if reached is None:
                    targets[symbol] = set(destinations)
                else:
                    reached.update(destinations)

        transitions: dict[T, str] = {}
        for symbol in alphabet:
            # Close the combined targets once; overlapping closures can be large.
            target_subset = epsilon_closure(frozenset(targets.get(symbol, ())))
            target_name = subset_to_name.get(target_subset)
            if target_name is None:
                target_name = f"q{len(subset_to_name)}"
                subset_to_name[target_subset] = target_name
                queue.append(target_subset)
            transitions[symbol] = target_name

        state_setup[subset_to_name[subset]] = (
            not nfa.accepting_states.isdisjoint(subset),
            transitions,
        )

    return state_setup


def compile_plain_regex_to_dfa(
    *,
    regex: Regex[T],
    alphabet: tuple[T, ...],
) -> Dfa[T]:
    used_symbols = regex.symbols()
    missing_symbols = used_symbols.difference(alphabet)
    if missing_symbols:
        raise ValueError(
            "`regex` contains symbols that are not in `alphabet`: "
            f"{sorted(repr(symbol) for symbol in missing_symbols)}"
        )

    nfa = regex_to_nfa(regex=regex, alphabet=alphabet)
    state_setup = determinize_complete_state_setup(nfa, alphabet=alphabet)
    return minimize_complete_dfa(state_setup, alphabet=alphabet)


def complement_dfa(dfa: Dfa[T]) -> Dfa[T]:
    for state in dfa.states:
        state.is_accepting = not state.is_accepting
    return dfa


def regex_to_dfa(
    *,
    regex: Regex[T] | ComplementRegex[T],
    alphabet: Sequence[T],
) -> Dfa[T]:
    alphabet_tuple, _ = validate_aalpy_alphabet(alphabet)

    if isinstance(regex, ComplementRegex):
        dfa = compile_plain_regex_to_dfa(
            regex=regex.regex,
            alphabet=alphabet_tuple,
        )
        return complement_dfa(dfa)

    if not isinstance(regex, Regex):
        raise TypeError("`regex` must be a `Regex` or `ComplementRegex`.")

    return compile_plain_regex_to_dfa(
        regex=regex,
        alphabet=alphabet_tuple,
    )
