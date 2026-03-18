"""
[JA]
このモジュールの発想の一部、すなわち「問題固有の custom oracle と既存の
汎用 oracle を chain する」という方向性は、以下の AALpy Discussion から
着想を得ています。
<https://github.com/DES-Lab/AALpy/discussions/53>

ただし、このファイルに含まれる具体的な API 設計、データ構造、制御フロー、
および実装は aalpy-compro 向けに独自に設計・実装したものであり、
Discussion 中のコード断片を転記したものではありません。

[EN]
Part of the high-level idea in this module—namely, chaining a problem-specific
custom oracle with an existing general-purpose oracle—was inspired by the AALpy
Discussion below.
<https://github.com/DES-Lab/AALpy/discussions/53>

However, the concrete API design, data structures, control flow, and
implementation in this file were designed and implemented independently for
`aalpy-compro`, and are not copied from code snippets in that Discussion.
"""

from collections.abc import Hashable, Sequence
from typing import Generic, TypeVar

from aalpy.automata import Dfa
from aalpy.base import Oracle, SUL

from .learning_property import WordFactory

Hashable_T = TypeVar("Hashable_T", bound=Hashable)


class ChainedEqOracle(Oracle, Generic[Hashable_T]):
    """
    複数の EqOracle を順番に試し、最初に見つかった counterexample を返す。
    """

    def __init__(
        self,
        alphabet: Sequence[Hashable_T],
        sul: SUL,
        oracles: Sequence[Oracle],
    ):
        super().__init__(list(alphabet), sul)
        self.oracles: list[Oracle] = list(oracles)

    def pull_stats(self, oracle: Oracle) -> None:
        self.num_queries += oracle.num_queries
        self.num_steps += oracle.num_steps
        oracle.num_queries = 0
        oracle.num_steps = 0

    def find_cex(self, hypothesis: Dfa[Hashable_T]) -> tuple[Hashable_T, ...] | None:
        for oracle in self.oracles:
            # AALpy 側で CacheSUL が差し替えられた後でも、
            # 子 oracle 全体が同じ SUL を使うように揃える。
            oracle.sul = self.sul
            oracle.alphabet = self.alphabet

            cex = oracle.find_cex(hypothesis)
            self.pull_stats(oracle)
            if cex is not None:
                return cex

        return None


class PrefixAwareEqOracle(Oracle, Generic[Hashable_T]):
    """
    check_word 関数を持つ EqOracle の基底クラス
    """

    def __init__(self, alphabet: Sequence[Hashable_T], sul: SUL) -> None:
        super().__init__(list(alphabet), sul)

    def check_word(
        self,
        hypothesis: Dfa[Hashable_T],
        word: tuple[Hashable_T, ...],
    ) -> tuple[Hashable_T, ...] | None:
        hyp_outs = hypothesis.compute_output_seq(hypothesis.initial_state, word)
        sul_outs = self.sul.query(word)

        self.num_queries += 1
        self.num_steps += len(word)

        assert len(hyp_outs) == len(sul_outs)

        if not word:
            return () if hyp_outs[-1] != sul_outs[-1] else None

        for i, (out_h, out_s) in enumerate(zip(hyp_outs, sul_outs), start=1):
            if out_h != out_s:
                return word[:i]

        return None


class FixedWordsEqOracle(PrefixAwareEqOracle[Hashable_T]):
    """
    指定した語について順番に試し、最初に見つかった counterexample を返す。
    """

    def __init__(
        self,
        alphabet: Sequence[Hashable_T],
        sul: SUL,
        word_factory: WordFactory[Hashable_T],
    ) -> None:
        super().__init__(list(alphabet), sul)
        self.word_factory = word_factory

    def find_cex(self, hypothesis: Dfa[Hashable_T]) -> tuple[Hashable_T, ...] | None:
        for word in self.word_factory():
            cex = self.check_word(hypothesis, word)
            if cex is not None:
                return cex
        return None
