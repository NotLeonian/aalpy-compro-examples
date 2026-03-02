import argparse

from .__internal.eq_oracles import WpSpec, RandomWpSpec, StatePrefixSpec, EqOracleSpec
from .__internal.learn_dfa import LearnConfig, learn_dfa_KV
from .__internal.dfa_to_cpp import dfa_to_dot_string, dot_to_cpp
from .__internal.load_property import load_property


def main() -> None:
    """
    path で受け取った alphabet や accepts の実装をもとに
    オートマトン学習を行い、cpp ファイルを出力する

    オプションはコマンドライン引数で与える
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        required=True,
        help="Path to .py file providing alphabet/accepts",
    )
    parser.add_argument(
        "--oracle", required=True, choices=["wp", "random_wp", "state_prefix"]
    )
    parser.add_argument("-o", "--output", default="learned.cpp")
    parser.add_argument("--namespace", default="learned_dfa")

    # KV params
    parser.add_argument("--cex-processing", default="rs")
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
    parser.add_argument("--walks-per-state", type=int)
    parser.add_argument("--walk-len", type=int)
    parser.add_argument("--max-tests", type=int)
    parser.add_argument("--depth-first", action="store_true")
    parser.add_argument("--no-depth-first", dest="depth_first", action="store_false")
    parser.set_defaults(depth_first=True)

    args = parser.parse_args()

    property = load_property(args.path)

    if args.oracle == "wp":
        if args.max_states is None:
            raise SystemExit("--oracle wp requires --max-states.")
        oracle_spec: EqOracleSpec = WpSpec(max_states=args.max_states)
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
    )

    res = dot_to_cpp(
        dot_text=dfa_to_dot_string(dfa),
        alphabet=property.alphabet,
        symbol_to_label=property.symbol_to_label,
        namespace=args.namespace,
        add_sink_if_missing=True,
    )
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(res)


if __name__ == "__main__":
    main()
