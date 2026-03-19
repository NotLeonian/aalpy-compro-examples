from dataclasses import dataclass
from typing import Literal, TypeAlias
import re

from .eq_oracles import EqOracleLiteral
from .learn_dfa import (
    CliCexProcessingLiteral,
    LearnAlgorithmLiteral,
    LStarClosingStrategyLiteral,
)
from .re_pattern import NAMESPACE_PATTERN, KEY_PATTERN
from .fullmatch import validate_fullmatch_pattern

RunKind: TypeAlias = Literal["learn", "regex", "common"]


@dataclass(frozen=True)
class MainArgs:
    """
    コマンドライン引数で与えられるオプションのクラス
    """

    print_completion: (
        None  # --print-completion が指定されているとき、その値はパーサーには渡されない
    )

    kind: RunKind
    path: str | None
    oracle: EqOracleLiteral | None

    algorithm: LearnAlgorithmLiteral

    namespace: str  # NAMESPACE_PATTERN に fullmatch するもの
    key: str | None  # KEY_PATTERN に fullmatch するもの（もしくは None）

    cex_processing: CliCexProcessingLiteral
    max_rounds: int | None
    no_cache: bool
    print_level: int

    closing_strategy: LStarClosingStrategyLiteral
    e_set_suffix_closed: bool
    all_prefixes_in_obs_table: bool

    max_states: int | None

    min_length: int
    expected_length: int
    num_tests: int

    walks_per_state: int
    walk_len: int
    max_tests: int | None
    depth_first: bool

    def __post_init__(self) -> None:
        def raise_value_error_if_non_fullmatch(
            *,
            pattern: re.Pattern[str],
            string: str,
            var_name: str,
        ) -> None:
            validate_fullmatch_pattern(
                pattern=pattern,
                string=string,
                exception=ValueError(f"{var_name} must match /{pattern.pattern}/."),
            )

        raise_value_error_if_non_fullmatch(
            pattern=NAMESPACE_PATTERN,
            string=self.namespace,
            var_name="namespace",
        )

        if self.key is None:
            if self.kind == "learn" or self.kind == "regex":
                raise ValueError(f'When --kind is "{self.kind}", --key is required.')
        else:
            raise_value_error_if_non_fullmatch(
                pattern=KEY_PATTERN,
                string=self.key,
                var_name="key",
            )

    def base_oracle_options_are_non_default(self) -> bool:
        """
        base oracle に関するオプションについて
        default 値以外を指定しているかどうかを判定する関数
        """

        return (
            self.max_states is not None
            or self.min_length != 1
            or self.expected_length != 10
            or self.num_tests != 1000
            or self.walks_per_state != 25
            or self.walk_len != 12
            or self.max_tests is not None
            or self.depth_first is not True
        )
