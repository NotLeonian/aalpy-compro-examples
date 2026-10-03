import unittest
from collections.abc import Callable, Hashable, Iterator, Sequence
from itertools import product
from typing import TypeAlias, cast
from unittest.mock import patch

from aalpy.automata import Dfa, DfaState
from aalpy_compro.__internal.eq_oracles import WpSpec
from aalpy_compro.__internal.learn_dfa import (
    KVLearnConfig,
    LearnConfigSpec,
    LStarLearnConfig,
    learn_dfa,
    learn_dfa_KV,
    learn_dfa_Lstar,
)
from aalpy_compro.errors import ConstraintViolationError

Learner: TypeAlias = Callable[..., Dfa[int]]


def words() -> Iterator[tuple[int, ...]]:
    for length in range(6):
        yield from product((0, 1), repeat=length)


def accepts(word: tuple[int, ...]) -> bool:
    return word.count(1) % 2 == 0


class LearningTests(unittest.TestCase):
    def entry_points(self) -> list[tuple[Learner, LearnConfigSpec]]:
        return [
            (learn_dfa, LStarLearnConfig(print_level=0)),
            (learn_dfa, KVLearnConfig(print_level=0)),
            (learn_dfa_Lstar, LStarLearnConfig(print_level=0)),
            (learn_dfa_KV, KVLearnConfig(print_level=0)),
        ]

    def test_learners_accept_the_same_language(self) -> None:
        for learner, config in self.entry_points():
            for oracle_spec in (None, WpSpec(max_states=2)):
                with self.subTest(
                    learner=learner.__name__, config=config, oracle=oracle_spec
                ):
                    dfa = learner(
                        alphabet=(0, 1),
                        accepts=accepts,
                        oracle_spec=oracle_spec,
                        learn_config=config,
                        fixed_eq_word_factory=words,
                    )
                    self.assertEqual(dfa.size, 2)
                    for word in words():
                        self.assertEqual(
                            dfa.compute_output_seq(dfa.initial_state, word)[-1],
                            accepts(word),
                            word,
                        )

    def test_algorithm_options_without_aalpy_cache(self) -> None:
        configs: list[LearnConfigSpec] = [
            LStarLearnConfig(
                cex_processing=None,
                closing_strategy="single",
                e_set_suffix_closed=True,
                all_prefixes_in_obs_table=False,
                cache_and_non_det_check=False,
                print_level=0,
            ),
            KVLearnConfig(
                cex_processing="linear_fwd",
                cache_and_non_det_check=False,
                print_level=0,
            ),
        ]
        for config in configs:
            with self.subTest(config=config):
                dfa = learn_dfa(
                    alphabet=(0, 1),
                    accepts=accepts,
                    oracle_spec=WpSpec(max_states=2),
                    learn_config=config,
                )
                for word in words():
                    self.assertEqual(
                        dfa.compute_output_seq(dfa.initial_state, word)[-1],
                        accepts(word),
                        word,
                    )

    def test_invalid_alphabet_is_rejected_before_querying(self) -> None:
        for learner, config in self.entry_points():
            for alphabet, message in (
                ((0, 0), "duplicates"),
                ((None,), "reserves `None`"),
                (([],), "hashable"),
            ):
                with (
                    self.subTest(
                        learner=learner.__name__, config=config, alphabet=alphabet
                    ),
                    self.assertRaisesRegex(ValueError, message),
                ):
                    learner(
                        alphabet=cast(Sequence[Hashable], alphabet),
                        accepts=lambda _: self.fail("Unexpected membership query"),
                        oracle_spec=None,
                        learn_config=config,
                    )

    def test_an_equivalence_oracle_is_required(self) -> None:
        for learner, config in self.entry_points():
            with (
                self.subTest(learner=learner.__name__, config=config),
                self.assertRaisesRegex(ValueError, "At least one"),
            ):
                learner(
                    alphabet=(0, 1),
                    accepts=accepts,
                    oracle_spec=None,
                    learn_config=config,
                )

    def test_wp_constraint_is_checked_after_learning(self) -> None:
        states = [DfaState("0"), DfaState("1"), DfaState("2")]
        oversized_dfa = Dfa(states[0], states)
        for learner, config in self.entry_points():
            algorithm = (
                "run_Lstar" if isinstance(config, LStarLearnConfig) else "run_KV"
            )
            with self.subTest(learner=learner.__name__, config=config):
                with (
                    patch(
                        f"aalpy_compro.__internal.learn_dfa.{algorithm}",
                        return_value=oversized_dfa,
                    ),
                    self.assertRaises(ConstraintViolationError) as caught,
                ):
                    learner(
                        alphabet=(0, 1),
                        accepts=accepts,
                        oracle_spec=WpSpec(max_states=2),
                        learn_config=config,
                    )
                self.assertEqual(caught.exception.constraint, "max_states")
                self.assertEqual(caught.exception.required, "<= 2")
                self.assertEqual(caught.exception.actual, 3)


if __name__ == "__main__":
    unittest.main()
