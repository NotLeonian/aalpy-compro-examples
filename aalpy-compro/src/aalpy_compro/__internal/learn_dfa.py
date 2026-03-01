from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from aalpy.automata import Dfa
from aalpy.learning_algs import run_KV

from .eq_oracles import WpSpec, EqOracleSpec, build_eq_oracle
from .sul import PrefixAcceptingSUL

type KVCexProcessing = Literal[
    "rs", "linear_fwd", "linear_bwd", "exponential_fwd", "exponential_bwd"
]


@dataclass
class LearnConfig:
    cex_processing: KVCexProcessing = "rs"
    max_learning_rounds: int | None = None
    cache_and_non_det_check: bool = True
    print_level: int = 2


def learn_dfa_KV[T](
    *,
    alphabet: Sequence[T],
    accepts: Callable[[tuple[T, ...]], bool],
    oracle_spec: EqOracleSpec,
    learn_config: LearnConfig,
) -> Dfa[T]:
    sul = PrefixAcceptingSUL(accepts)
    eq_oracle = build_eq_oracle(alphabet, sul, oracle_spec)

    dfa = run_KV(
        list(alphabet),
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

    if isinstance(oracle_spec, WpSpec) and dfa.size > oracle_spec.max_states:
        raise RuntimeError(
            f"Bound violated: learned DFA has {dfa.size} states > max_states={oracle_spec.max_states}."
        )

    return dfa
