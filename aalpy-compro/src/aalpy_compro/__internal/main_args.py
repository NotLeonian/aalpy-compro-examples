from dataclasses import dataclass
from typing import Literal, TypeAlias
import re

from .eq_oracles import EqOracleLiteral
from .learn_dfa import KVCexProcessing
from .re_pattern import NAMESPACE_PATTERN, KEY_PATTERN
from .fullmatch import validate_fullmatch_pattern

RunKind: TypeAlias = Literal["learn", "common"]


@dataclass(frozen=True)
class MainArgs:
    """
    コマンドライン引数で与えられるオプションのクラス
    """

    kind: RunKind
    path: str | None
    oracle: EqOracleLiteral | None
    namespace: str  # NAMESPACE_PATTERN に fullmatch するもの
    key: str  # KEY_PATTERN に fullmatch するもの
    cex_processing: KVCexProcessing
    max_rounds: int | None
    no_cache: bool
    print_level: int
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
            pattern=NAMESPACE_PATTERN, string=self.namespace, var_name="namespace"
        )
        raise_value_error_if_non_fullmatch(
            pattern=KEY_PATTERN, string=self.key, var_name="key"
        )
