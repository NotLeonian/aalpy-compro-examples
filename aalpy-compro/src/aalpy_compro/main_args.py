from dataclasses import dataclass
from typing import Literal, TypeAlias

from .__internal.eq_oracles import EqOracleLiteral
from .__internal.learn_dfa import KVCexProcessing

RunKind: TypeAlias = Literal["learn", "common"]


@dataclass(frozen=True)
class MainArgs:
    """
    コマンドライン引数で与えられるオプションのクラス
    """

    kind: RunKind
    path: str | None
    oracle: EqOracleLiteral | None
    namespace: str
    key: str
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
