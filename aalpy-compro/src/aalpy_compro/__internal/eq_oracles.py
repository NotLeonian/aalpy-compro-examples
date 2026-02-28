from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from aalpy.base import SUL
from aalpy.oracles import WpMethodEqOracle, RandomWpMethodEqOracle, StatePrefixEqOracle

type EqOracle = WpMethodEqOracle | RandomWpMethodEqOracle | StatePrefixEqOracle


@dataclass(frozen=True)
class WpSpec:
    kind: Literal["wp"] = field(default="wp", init=False)
    max_states: int


@dataclass(frozen=True)
class RandomWpSpec:
    kind: Literal["random_wp"] = field(default="random_wp", init=False)
    min_length: int
    expected_length: int
    num_tests: int


@dataclass(frozen=True)
class StatePrefixSpec:
    kind: Literal["state_prefix"] = field(default="state_prefix", init=False)
    walks_per_state: int
    walk_len: int
    max_tests: int | None
    depth_first: bool


type EqOracleSpec = WpSpec | RandomWpSpec | StatePrefixSpec


def build_eq_oracle[T](
    alphabet: Sequence[T],
    sul: SUL,
    spec: EqOracleSpec,
) -> EqOracle:
    a = list(alphabet)

    if spec.kind == "wp":
        if spec.max_states <= 0:
            raise ValueError("WpSpec.max_states must be positive.")
        return WpMethodEqOracle(a, sul, max_number_of_states=spec.max_states)

    if spec.kind == "random_wp":
        if spec.min_length < 0 or spec.expected_length < 0 or spec.num_tests <= 0:
            raise ValueError("RandomWpSpec parameters are invalid.")
        return RandomWpMethodEqOracle(
            a,
            sul,
            min_length=spec.min_length,
            expected_length=spec.expected_length,
            num_tests=spec.num_tests,
        )

    if spec.kind == "state_prefix":
        if spec.walks_per_state <= 0 or spec.walk_len <= 0:
            raise ValueError(
                "StatePrefixSpec.walks_per_state and walk_len must be positive."
            )
        return StatePrefixEqOracle(
            a,
            sul,
            walks_per_state=spec.walks_per_state,
            walk_len=spec.walk_len,
            max_tests=spec.max_tests,
            depth_first=spec.depth_first,
        )

    raise ValueError(f"Unknown spec.kind: {getattr(spec, 'kind', None)}")
