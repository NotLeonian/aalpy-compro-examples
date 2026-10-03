import random
import unittest
from collections import deque
from collections.abc import Hashable
from itertools import combinations
from typing import TypeVar

from aalpy.automata import Dfa
from aalpy_compro.__internal.minimize_dfa import minimize_complete_dfa

T = TypeVar("T", bound=Hashable)


def minimum_reachable_size(
    setup: dict[str, tuple[bool, dict[T, str]]], alphabet: tuple[T, ...]
) -> int:
    reachable = {next(iter(setup))}
    queue = deque(reachable)
    while queue:
        for target in setup[queue.popleft()][1].values():
            if target not in reachable:
                reachable.add(target)
                queue.append(target)

    pairs = list(combinations(sorted(reachable), 2))
    distinct = {
        frozenset((left, right))
        for left, right in pairs
        if setup[left][0] != setup[right][0]
    }
    changed = True
    while changed:
        changed = False
        for left, right in pairs:
            pair = frozenset((left, right))
            if pair not in distinct and any(
                frozenset((setup[left][1][symbol], setup[right][1][symbol])) in distinct
                for symbol in alphabet
            ):
                distinct.add(pair)
                changed = True

    representatives: list[str] = []
    for state in sorted(reachable):
        if all(frozenset((state, rep)) in distinct for rep in representatives):
            representatives.append(state)
    return len(representatives)


class MinimizeDfaTests(unittest.TestCase):
    def assert_equivalent(
        self,
        setup: dict[str, tuple[bool, dict[T, str]]],
        dfa: Dfa[T],
        alphabet: tuple[T, ...],
    ) -> None:
        initial_pair = (next(iter(setup)), dfa.initial_state)
        seen = {initial_pair}
        queue = deque([initial_pair])
        while queue:
            original, minimized = queue.popleft()
            self.assertEqual(setup[original][0], minimized.is_accepting)
            self.assertEqual(tuple(minimized.transitions), alphabet)
            for symbol in alphabet:
                pair = (setup[original][1][symbol], minimized.transitions[symbol])
                if pair not in seen:
                    seen.add(pair)
                    queue.append(pair)

        self.assertEqual(dfa.size, minimum_reachable_size(setup, alphabet))
        self.assertIn(dfa.initial_state, dfa.states)
        self.assertEqual(dfa.current_state, dfa.initial_state)
        self.assertEqual(len({state.state_id for state in dfa.states}), dfa.size)
        self.assertEqual({state for _, state in seen}, set(dfa.states))

        for state in dfa.states:
            prefix = state.prefix
            assert prefix is not None
            self.assertEqual(prefix, dfa.get_shortest_path(dfa.initial_state, state))
            reached = dfa.initial_state
            for symbol in prefix:
                reached = reached.transitions[symbol]
            self.assertIs(reached, state)

    def test_all_accepting_or_rejecting_states_merge(self) -> None:
        for accepting in (False, True):
            with self.subTest(accepting=accepting):
                setup = {
                    "initial": (accepting, {0: "second", 1: "third"}),
                    "second": (accepting, {0: "third", 1: "initial"}),
                    "third": (accepting, {0: "initial", 1: "second"}),
                }
                dfa = minimize_complete_dfa(setup, alphabet=(0, 1))
                self.assertEqual(dfa.size, 1)
                self.assertEqual(dfa.initial_state.state_id, "initial")
                self.assert_equivalent(setup, dfa, (0, 1))

    def test_equivalent_branches_merge_and_keep_first_representative(self) -> None:
        setup = {
            "initial": (False, {0: "left", 1: "right"}),
            "right": (True, {0: "sink", 1: "initial"}),
            "left": (True, {0: "sink", 1: "initial"}),
            "sink": (False, {0: "sink", 1: "sink"}),
        }
        dfa = minimize_complete_dfa(setup, alphabet=(0, 1))
        self.assertEqual(dfa.size, 3)
        self.assertEqual(
            [state.state_id for state in dfa.states], ["initial", "right", "sink"]
        )
        self.assert_equivalent(setup, dfa, (0, 1))

    def test_unreachable_states_are_omitted(self) -> None:
        setup = {
            "initial": (False, {0: "accepting", 1: "initial"}),
            "accepting": (True, {0: "initial", 1: "accepting"}),
            "unreachable": (True, {0: "unreachable", 1: "unreachable"}),
        }
        dfa = minimize_complete_dfa(setup, alphabet=(0, 1))
        self.assertEqual(dfa.size, 2)
        self.assert_equivalent(setup, dfa, (0, 1))

    def test_empty_alphabet_keeps_only_initial_state(self) -> None:
        setup: dict[str, tuple[bool, dict[int, str]]] = {
            "initial": (True, {}),
            "unreachable": (False, {}),
        }
        dfa = minimize_complete_dfa(setup, alphabet=())
        self.assertTrue(dfa.initial_state.is_accepting)
        self.assert_equivalent(setup, dfa, ())

    def test_mixed_hashable_symbols_keep_alphabet_order(self) -> None:
        alphabet: tuple[Hashable, ...] = ((1, 2), "a", 7)
        setup: dict[str, tuple[bool, dict[Hashable, str]]] = {
            "initial": (False, {(1, 2): "accepting", "a": "initial", 7: "accepting"}),
            "accepting": (True, {(1, 2): "initial", "a": "accepting", 7: "initial"}),
        }
        dfa = minimize_complete_dfa(setup, alphabet=alphabet)
        self.assertEqual(dfa.states[1].prefix, ((1, 2),))
        self.assert_equivalent(setup, dfa, alphabet)

    def test_empty_setup_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "initial state"):
            minimize_complete_dfa({}, alphabet=(0, 1))

    def test_random_complete_automata(self) -> None:
        rng = random.Random(73569)
        for size in range(1, 14):
            for case in range(12):
                alphabet = tuple(range(case % 4))
                setup = {
                    f"q{state}": (
                        bool(rng.randrange(2)),
                        {symbol: f"q{rng.randrange(size)}" for symbol in alphabet},
                    )
                    for state in range(size)
                }
                with self.subTest(size=size, case=case):
                    dfa = minimize_complete_dfa(setup, alphabet=alphabet)
                    self.assert_equivalent(setup, dfa, alphabet)
                    reachable = {"q0"}
                    queue = deque(["q0"])
                    while queue:
                        for target in setup[queue.popleft()][1].values():
                            if target not in reachable:
                                reachable.add(target)
                                queue.append(target)
                    reachable_setup = {
                        name: setup[name] for name in setup if name in reachable
                    }
                    original = Dfa.from_state_setup(reachable_setup)
                    original.minimize()
                    self.assertEqual(dfa.size, original.size)

    def test_long_chain_has_all_shortest_prefixes_without_recursion(self) -> None:
        length = 1500
        setup = {
            f"q{index}": (index == length, {0: f"q{min(index + 1, length)}"})
            for index in range(length + 1)
        }
        dfa = minimize_complete_dfa(setup, alphabet=(0,))
        self.assertEqual(dfa.size, length + 1)
        for index, state in enumerate(dfa.states):
            self.assertEqual(state.prefix, (0,) * index)
            self.assertEqual(state.is_accepting, index == length)


if __name__ == "__main__":
    unittest.main()
