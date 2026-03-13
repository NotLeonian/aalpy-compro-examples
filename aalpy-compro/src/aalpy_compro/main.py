from collections.abc import Callable
import argparse
import re

from .__internal.names import DIST_NAME
from .__internal.get_version import get_version
from .__internal.eq_oracles import (
    WpSpec,
    RandomWpSpec,
    StatePrefixSpec,
    EqOracleList,
    EqOracleSpec,
)
from .__internal.learn_dfa import KVCexProcessingList, LearnConfig, learn_dfa_KV
from .__internal.dfa_to_cpp import dfa_to_dot_string, dot_to_cpp
from .__internal.cpp_common_dfa_struct import common_dfa_struct
from .__internal.load_property import load_property
from .__internal.re_pattern import NAMESPACE_PATTERN, KEY_PATTERN
from .__internal.fullmatch import validate_fullmatch_pattern
from .__internal.main_args import MainArgs


def main() -> int:
    """
    path で受け取った alphabet や accepts の実装をもとに
    オートマトン学習を行い、cpp ファイルを出力する

    オプションはコマンドライン引数で与える
    """

    def parse_fullmatch_pattern(
        *,
        pattern: re.Pattern[str],
        arg_name: str,
    ) -> Callable[[str], str]:
        def __validator(value: str) -> str:
            validate_fullmatch_pattern(
                pattern=pattern,
                string=value,
                exception=argparse.ArgumentTypeError(
                    f"{arg_name} must match /{pattern.pattern}/."
                ),
            )

            return value

        return __validator

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{DIST_NAME} {get_version()}",
    )

    parser.add_argument(
        "--kind",
        choices=["learn", "common"],
        help='Select "learn" or "common" (default: "learn").',
        default="learn",
    )
    parser.add_argument(
        "--path",
        help="Path to .py file providing alphabet/accepts",
        default=None,
    )
    parser.add_argument(
        "--oracle",
        choices=EqOracleList,
        default=None,
    )
    parser.add_argument(
        "--namespace",
        type=parse_fullmatch_pattern(pattern=NAMESPACE_PATTERN, arg_name="namespace"),
        help=f"--namespace must match /{NAMESPACE_PATTERN.pattern}/.",
        default="learned_dfa",
    )
    parser.add_argument(
        "--key",
        type=parse_fullmatch_pattern(pattern=KEY_PATTERN, arg_name="key"),
        help="\n".join(
            [
                f"--key must match /{KEY_PATTERN.pattern}/.",
                'When --kind is "learn", effectively required.',
                "Each name should be unique.",
            ]
        ),
        default=None,
    )

    # KV params
    parser.add_argument(
        "--cex-processing",
        choices=KVCexProcessingList,
        default="rs",
    )
    parser.add_argument("--max-rounds", type=int, default=None)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--print-level", type=int, default=2)

    # Wp params
    # max-states には default の値を設定していないことに注意
    parser.add_argument("--max-states", type=int, default=None)

    # RandomWp params
    parser.add_argument("--min-length", type=int, default=1)
    parser.add_argument("--expected-length", type=int, default=10)
    parser.add_argument("--num-tests", type=int, default=1000)

    # StatePrefix params
    parser.add_argument("--walks-per-state", type=int, default=25)
    parser.add_argument("--walk-len", type=int, default=12)
    parser.add_argument("--max-tests", type=int, default=None)
    parser.add_argument("--depth-first", action="store_true")
    parser.add_argument("--no-depth-first", dest="depth_first", action="store_false")
    parser.set_defaults(depth_first=True)

    args = MainArgs(**vars(parser.parse_args()))

    if args.kind == "learn":
        if args.path is None:
            raise SystemExit("--kind learn requires --path.")
        if args.oracle is None:
            raise SystemExit("--kind learn requires --oracle.")

        property = load_property(args.path)

        oracle_spec: EqOracleSpec

        if args.oracle == "wp":
            if args.max_states is None:
                raise SystemExit("--oracle wp requires --max-states.")
            oracle_spec = WpSpec(max_states=args.max_states)
        elif args.oracle == "random_wp":
            oracle_spec = RandomWpSpec(
                min_length=args.min_length,
                expected_length=args.expected_length,
                num_tests=args.num_tests,
            )
        else:  # args.oracle == "state_prefix"
            oracle_spec = StatePrefixSpec(
                walks_per_state=args.walks_per_state,
                walk_len=args.walk_len,
                max_tests=args.max_tests,
                depth_first=args.depth_first,
            )

        learn_config = LearnConfig(
            cex_processing=args.cex_processing,
            max_learning_rounds=args.max_rounds,
            cache_and_non_det_check=(not args.no_cache),
            print_level=args.print_level,
        )

        dfa = learn_dfa_KV(
            alphabet=property.alphabet,
            accepts=property.accepts,
            oracle_spec=oracle_spec,
            learn_config=learn_config,
            fixed_eq_word_factory=property.fixed_eq_word_factory,
        )

        assert args.key is not None  # MainArgs の __post_init__ で弾かれている
        res = dot_to_cpp(
            dot_text=dfa_to_dot_string(dfa),
            alphabet=property.alphabet,
            symbol_to_label=property.symbol_to_label,
            namespace=args.namespace,
            key=args.key,
            add_sink_if_missing=True,
        )

        print(res)
    else:
        res = common_dfa_struct(namespace=args.namespace)

        print(res)

    return 0


if __name__ == "__main__":
    main()
