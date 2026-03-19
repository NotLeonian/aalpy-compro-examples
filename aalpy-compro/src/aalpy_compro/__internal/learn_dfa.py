from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias, TypeVar, Any, cast

from aalpy.automata import Dfa
from aalpy.base import Oracle, SUL
from aalpy.learning_algs import run_Lstar, run_KV

from .validation_for_aalpy import validate_aalpy_alphabet
from .eq_oracles import WpSpec, EqOracleSpec, build_eq_oracle
from .learning_property import WordFactory
from .prefix_accepting_sul import PrefixAcceptingSUL
from ..errors import ConstraintViolationError

T = TypeVar("T", bound=Hashable)

LearnAlgorithmList: list[str] = ["lstar", "kv"]
LearnAlgorithmLiteral: TypeAlias = Literal["lstar", "kv"]

LStarCexProcessingList: list[str] = [
    "none",
    "rs",
    "longest_prefix",
    "linear_fwd",
    "linear_bwd",
    "exponential_fwd",
    "exponential_bwd",
]
LStarRuntimeCexProcessingNonNoneLiteral: TypeAlias = Literal[
    "rs",
    "longest_prefix",
    "linear_fwd",
    "linear_bwd",
    "exponential_fwd",
    "exponential_bwd",
]
LStarRuntimeCexProcessingLiteral: TypeAlias = (
    LStarRuntimeCexProcessingNonNoneLiteral | None
)
LStarCexProcessingLiteral: TypeAlias = (
    LStarRuntimeCexProcessingNonNoneLiteral | Literal["none"]
)

KVCexProcessingList: list[str] = [
    "rs",
    "linear_fwd",
    "linear_bwd",
    "exponential_fwd",
    "exponential_bwd",
]
KVCexProcessingLiteral: TypeAlias = Literal[
    "rs",
    "linear_fwd",
    "linear_bwd",
    "exponential_fwd",
    "exponential_bwd",
]

# run_KV の cex_processing で許される文字列は全て
# run_Lstar の cex_processing でも許される
CliCexProcessingList: list[str] = LStarCexProcessingList
CliCexProcessingLiteral: TypeAlias = LStarCexProcessingLiteral

LStarClosingStrategyList: list[str] = [
    "shortest_first",
    "longest_first",
    "single",
]
LStarClosingStrategyLiteral: TypeAlias = Literal[
    "shortest_first",
    "longest_first",
    "single",
]


@dataclass(frozen=True)
class LStarLearnConfig:
    cex_processing: LStarRuntimeCexProcessingLiteral = "rs"
    closing_strategy: LStarClosingStrategyLiteral = "shortest_first"
    e_set_suffix_closed: bool = False
    all_prefixes_in_obs_table: bool = True
    max_learning_rounds: int | None = None
    cache_and_non_det_check: bool = True
    print_level: int = 2


@dataclass
class KVLearnConfig:
    cex_processing: KVCexProcessingLiteral = "rs"
    max_learning_rounds: int | None = None
    cache_and_non_det_check: bool = True
    print_level: int = 2


LearnConfigSpec: TypeAlias = KVLearnConfig | LStarLearnConfig


def check_wp_constraint(dfa: Dfa[T], oracle_spec: EqOracleSpec | None) -> None:
    if not isinstance(oracle_spec, WpSpec):
        return

    if dfa.size > oracle_spec.max_states:
        raise ConstraintViolationError(
            constraint="max_states",
            required=f"<= {oracle_spec.max_states}",
            actual=dfa.size,
        )


def normalize_lstar_cex_processing(
    value: LStarCexProcessingLiteral,
) -> LStarRuntimeCexProcessingLiteral:
    match value:
        case "none":
            return None
        case (
            "rs"
            | "longest_prefix"
            | "linear_fwd"
            | "linear_bwd"
            | "exponential_fwd"
            | "exponential_bwd"
        ):
            return value
        case _:
            raise SystemExit(
                f"--algorithm lstar does not support --cex-processing {value!r}."
            )


def normalize_kv_cex_processing(
    value: CliCexProcessingLiteral,
) -> KVCexProcessingLiteral:
    match value:
        case "rs" | "linear_fwd" | "linear_bwd" | "exponential_fwd" | "exponential_bwd":
            return value
        case _:
            raise SystemExit(
                f"--algorithm kv does not support --cex-processing {value!r}."
            )


def learn_dfa(
    *,
    alphabet: Sequence[T],
    accepts: Callable[[tuple[T, ...]], bool],
    oracle_spec: EqOracleSpec | None,
    learn_config: LearnConfigSpec,
    fixed_eq_word_factory: WordFactory[T] | None = None,
) -> Dfa[T]:
    if isinstance(learn_config, LStarLearnConfig):
        return learn_dfa_Lstar(
            alphabet=alphabet,
            accepts=accepts,
            oracle_spec=oracle_spec,
            learn_config=learn_config,
            fixed_eq_word_factory=fixed_eq_word_factory,
        )
    else:  # isinstance(learn_config, KVLearnConfig)
        return learn_dfa_KV(
            alphabet=alphabet,
            accepts=accepts,
            oracle_spec=oracle_spec,
            learn_config=learn_config,
            fixed_eq_word_factory=fixed_eq_word_factory,
        )


def run_Lstar_compat(
    *,
    alphabet_list: list[T],
    sul: SUL,
    eq_oracle: Oracle,
    learn_config: LStarLearnConfig,
) -> Dfa[T]:
    """
    run_Lstar について
    型チェックが誤反応しないためのヘルパー
    """

    dfa = run_Lstar(
        alphabet_list,
        sul,
        eq_oracle,
        automaton_type="dfa",
        closing_strategy=learn_config.closing_strategy,
        cex_processing=cast(Any, learn_config.cex_processing),
        e_set_suffix_closed=learn_config.e_set_suffix_closed,
        all_prefixes_in_obs_table=learn_config.all_prefixes_in_obs_table,
        max_learning_rounds=learn_config.max_learning_rounds,
        cache_and_non_det_check=learn_config.cache_and_non_det_check,
        return_data=False,
        print_level=learn_config.print_level,
    )
    assert isinstance(dfa, Dfa)

    return dfa


def learn_dfa_Lstar(
    *,
    alphabet: Sequence[T],
    accepts: Callable[[tuple[T, ...]], bool],
    oracle_spec: EqOracleSpec | None,
    learn_config: LStarLearnConfig,
    fixed_eq_word_factory: WordFactory[T] | None = None,
) -> Dfa[T]:
    alphabet_tuple, _ = validate_aalpy_alphabet(alphabet)

    sul = PrefixAcceptingSUL(accepts)
    eq_oracle = build_eq_oracle(
        alphabet_tuple,
        sul,
        oracle_spec,
        fixed_eq_word_factory=fixed_eq_word_factory,
    )

    dfa = run_Lstar_compat(
        alphabet_list=list(alphabet_tuple),
        sul=sul,
        eq_oracle=eq_oracle,
        learn_config=learn_config,
    )

    check_wp_constraint(dfa, oracle_spec)
    return dfa


def learn_dfa_KV(
    *,
    alphabet: Sequence[T],
    accepts: Callable[[tuple[T, ...]], bool],
    oracle_spec: EqOracleSpec | None,
    learn_config: KVLearnConfig,
    fixed_eq_word_factory: WordFactory[T] | None = None,
) -> Dfa[T]:
    alphabet_tuple, _ = validate_aalpy_alphabet(alphabet)

    sul = PrefixAcceptingSUL(accepts)
    eq_oracle = build_eq_oracle(
        alphabet_tuple,
        sul,
        oracle_spec,
        fixed_eq_word_factory=fixed_eq_word_factory,
    )

    dfa = run_KV(
        list(alphabet_tuple),
        sul,
        eq_oracle,
        automaton_type="dfa",
        cex_processing=learn_config.cex_processing,
        max_learning_rounds=learn_config.max_learning_rounds,
        cache_and_non_det_check=learn_config.cache_and_non_det_check,
        return_data=False,
        print_level=learn_config.print_level,
    )

    assert isinstance(dfa, Dfa)
    check_wp_constraint(dfa, oracle_spec)

    return dfa
