import itertools
import random
import unittest
from collections.abc import Hashable
from typing import TypeVar

from aalpy.automata import Dfa
from aalpy_compro.__internal.regex_to_dfa import (
    Nfa,
    determinize_complete_state_setup,
    regex_to_dfa,
)
from aalpy_compro.regex import Regex

T = TypeVar("T", bound=Hashable)


def bounded_language(
    regex: Regex[T], alphabet: tuple[T, ...], max_length: int
) -> set[tuple[T, ...]]:
    languages: dict[int, set[tuple[T, ...]]] = {}

    def concatenate(
        left: set[tuple[T, ...]], right: set[tuple[T, ...]]
    ) -> set[tuple[T, ...]]:
        return {a + b for a in left for b in right if len(a) + len(b) <= max_length}

    def evaluate(node: Regex[T]) -> set[tuple[T, ...]]:
        cached = languages.get(id(node))
        if cached is not None:
            return cached
        if node._kind == "empty_set":
            result: set[tuple[T, ...]] = set()
        elif node._kind == "epsilon":
            result = {()}
        elif node._kind == "symbol":
            result = {(node.require_symbol_payload(),)} if max_length else set()
        elif node._kind == "dot":
            result = {(symbol,) for symbol in alphabet} if max_length else set()
        elif node._kind == "union":
            result = set().union(*(evaluate(part) for part in node._parts))
        elif node._kind == "concat":
            result = {()}
            for part in node._parts:
                result = concatenate(result, evaluate(part))
        elif node._kind == "star":
            part_language = evaluate(node._parts[0])
            result = {()}
            frontier = result
            while frontier:
                frontier = concatenate(frontier, part_language) - result
                result |= frontier
        else:
            raise AssertionError(node._kind)
        languages[id(node)] = result
        return result

    return evaluate(regex)


def accepts(dfa: Dfa[T], word: tuple[T, ...]) -> bool:
    state = dfa.initial_state
    for symbol in word:
        state = state.transitions[symbol]
    return state.is_accepting


class RegexToDfaTests(unittest.TestCase):
    def assert_complete_minimal_dfa(self, dfa: Dfa[T], alphabet: tuple[T, ...]) -> None:
        self.assertIn(dfa.initial_state, dfa.states)
        self.assertEqual(len(set(dfa.states)), len(dfa.states))
        reached = {dfa.initial_state}
        frontier = [dfa.initial_state]
        while frontier:
            state = frontier.pop()
            self.assertEqual(set(state.transitions), set(alphabet))
            for target in state.transitions.values():
                self.assertIn(target, dfa.states)
                if target not in reached:
                    reached.add(target)
                    frontier.append(target)
        self.assertEqual(reached, set(dfa.states))

        for state in dfa.states:
            prefix = state.prefix
            self.assertIsNotNone(prefix)
            assert prefix is not None
            target = dfa.initial_state
            for symbol in prefix:
                target = target.transitions[symbol]
            self.assertIs(target, state)

        for left, right in itertools.combinations(dfa.states, 2):
            pairs = [(left, right)]
            visited = {(left, right)}
            while pairs:
                first, second = pairs.pop()
                if first.is_accepting != second.is_accepting:
                    break
                for symbol in alphabet:
                    pair = (first.transitions[symbol], second.transitions[symbol])
                    if pair not in visited:
                        visited.add(pair)
                        pairs.append(pair)
            else:
                self.fail(
                    f"States {left.state_id!r} and {right.state_id!r} are equivalent"
                )

    def assert_language(
        self, regex: Regex[T], alphabet: tuple[T, ...], max_length: int = 4
    ) -> None:
        expected = bounded_language(regex, alphabet, max_length)
        for complement in (False, True):
            with self.subTest(complement=complement):
                dfa = regex_to_dfa(
                    regex=~regex if complement else regex, alphabet=alphabet
                )
                self.assert_complete_minimal_dfa(dfa, alphabet)
                for length in range(max_length + 1):
                    for word in itertools.product(alphabet, repeat=length):
                        self.assertEqual(
                            accepts(dfa, word),
                            (word in expected) != complement,
                            f"Unexpected acceptance of {word!r} by {regex!s}",
                        )

    def test_generated_expressions_match_bounded_language(self) -> None:
        atoms = [
            Regex[str].empty_set(),
            Regex[str].epsilon(),
            Regex[str].dot(),
            Regex.symbol("a"),
            Regex.symbol("b"),
        ]
        expressions = atoms + [Regex("star", _parts=(atom,)) for atom in atoms]
        for left, right in itertools.product(atoms, repeat=2):
            expressions.extend(
                (
                    Regex("union", _parts=(left, right)),
                    Regex("concat", _parts=(left, right)),
                )
            )
        rng = random.Random(5471)
        small_expressions = tuple(expressions)
        for _ in range(40):
            left, right = rng.choices(small_expressions, k=2)
            expressions.append(
                Regex("union", _parts=(left, right)).star()
                + Regex("concat", _parts=(right, left))
            )

        for index, regex in enumerate(expressions):
            with self.subTest(expression=index):
                self.assert_language(regex, ("a", "b"))

    def test_empty_alphabet(self) -> None:
        for regex in (
            Regex[str].empty_set(),
            Regex[str].epsilon(),
            Regex[str].dot(),
            Regex[str].dot().star(),
            Regex("concat", _parts=(Regex[str].epsilon(), Regex[str].dot())),
        ):
            with self.subTest(regex=str(regex)):
                self.assert_language(regex, ())

    def test_heterogeneous_symbols_and_unused_alphabet_symbols(self) -> None:
        alphabet: tuple[Hashable, ...] = (1, "x", ("tag",), frozenset({2}))
        regex = Regex[Hashable].symbol(1).union(Regex[Hashable].symbol(("tag",)))
        self.assert_language(regex.star() + Regex[Hashable].dot(), alphabet, 3)

    def test_shared_subexpressions_keep_independent_occurrences(self) -> None:
        shared = Regex.word("ab").optional()
        regex = Regex("concat", _parts=(shared, shared, shared))
        self.assert_language(regex, ("a", "b"), 6)

    def test_deep_ast_does_not_require_python_recursion(self) -> None:
        regex = Regex[str].symbol("a")
        for _ in range(1500):
            regex = Regex("star", _parts=(regex,))
        alphabet: tuple[str, ...] = ("a", "b")
        dfa: Dfa[str] = regex_to_dfa(regex=regex, alphabet=alphabet)
        self.assert_complete_minimal_dfa(dfa, alphabet)
        self.assertEqual(len(dfa.states), 2)
        for word in ((), ("a",), ("a",) * 2000):
            self.assertTrue(accepts(dfa, word))
        self.assertFalse(accepts(dfa, ("a", "b")))

    def test_cycles_are_rejected_even_after_hashing(self) -> None:
        regex = Regex.symbol("a").star()
        hash(regex)
        object.__setattr__(regex, "_parts", (regex,))
        for expression in (regex, ~regex):
            with self.assertRaisesRegex(
                ValueError, r"^Cyclic Regex is not supported\.$"
            ):
                regex_to_dfa(regex=expression, alphabet=("a",))

    def test_missing_symbols_preserve_error(self) -> None:
        regex = Regex[Hashable].symbol(1).union(Regex[Hashable].symbol("x"))
        for expression in (regex, ~regex):
            with self.assertRaises(ValueError) as error:
                regex_to_dfa(regex=expression, alphabet=())
            self.assertEqual(
                str(error.exception),
                "`regex` contains symbols that are not in `alphabet`: "
                f"{sorted((repr(1), repr('x')))}",
            )

    def test_alphabet_validation_precedes_regex_validation(self) -> None:
        regex = Regex[Hashable].symbol("missing")
        for alphabet, message in (
            (("a", "a"), "`alphabet` must not contain duplicates."),
            (
                (None,),
                (
                    "`None` cannot be used as an input symbol with AALpy-backed "
                    "functionality, because AALpy reserves `None` as the empty-word "
                    "/ no-input marker."
                ),
            ),
        ):
            with self.subTest(alphabet=alphabet):
                with self.assertRaises(ValueError) as error:
                    regex_to_dfa(regex=regex, alphabet=alphabet)
                self.assertEqual(str(error.exception), message)

    def test_determinization_handles_epsilon_cycles_and_sparse_state_ids(self) -> None:
        nfa = Nfa(
            start_state=10,
            accepting_states=frozenset({40, 1000}),
            symbol_transitions={20: {"a": {20, 40}}, 40: {"b": {40}}},
            epsilon_transitions={10: {20, 30}, 20: {30}, 30: {10}, 1000: {1000}},
        )
        setup = determinize_complete_state_setup(nfa, alphabet=("a", "b"))
        dfa = Dfa.from_state_setup(setup)
        self.assertEqual(setup["q0"][0], False)
        for state in dfa.states:
            self.assertEqual(set(state.transitions), {"a", "b"})
        for length in range(7):
            for word in itertools.product(("a", "b"), repeat=length):
                self.assertEqual(
                    accepts(dfa, word),
                    bool(word) and word[0] == "a" and "ba" not in "".join(word),
                )


if __name__ == "__main__":
    unittest.main()
