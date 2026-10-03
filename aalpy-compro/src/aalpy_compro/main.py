import sys
from collections.abc import Sequence

from .__internal.cli import parse_args
from .__internal.cpp_common_dfa_struct import common_dfa_struct
from .__internal.dfa_to_cpp import aalpy_dfa_to_cpp
from .__internal.learn_dfa import learn_dfa
from .__internal.learning_property import load_learning_property
from .__internal.main_args import MainArgs
from .__internal.regex_property import load_regex_property
from .__internal.regex_to_dfa import regex_to_dfa


def _learn_cpp(args: MainArgs) -> str:
    if args.path is None:
        raise SystemExit("--kind learn requires --path.")

    learning_property = load_learning_property(args.path)

    if args.oracle is None and learning_property.fixed_eq_word_factory is None:
        raise SystemExit(
            "--kind learn requires at least one equivalence oracle source: "
            "--oracle, `eq_words`/`iter_eq_words`."
        )

    if args.oracle is None and args.base_oracle_options_are_non_default():
        print(
            "Warning: base-oracle-specific options require --oracle.",
            file=sys.stderr,
        )

    oracle_spec = args.build_oracle_spec()
    learn_config = args.build_learn_config()

    dfa = learn_dfa(
        alphabet=learning_property.alphabet,
        accepts=learning_property.accepts,
        oracle_spec=oracle_spec,
        learn_config=learn_config,
        fixed_eq_word_factory=learning_property.fixed_eq_word_factory,
    )

    assert args.key is not None  # MainArgs の __post_init__ で弾かれている
    return aalpy_dfa_to_cpp(
        dfa=dfa,
        alphabet=learning_property.alphabet,
        symbol_to_label=learning_property.symbol_to_label,
        namespace=args.namespace,
        key=args.key,
        add_sink_if_missing=True,
    )


def _regex_cpp(args: MainArgs) -> str:
    if args.path is None:
        raise SystemExit("--kind regex requires --path.")

    regex_property = load_regex_property(args.path)
    dfa = regex_to_dfa(
        regex=regex_property.regex,
        alphabet=regex_property.alphabet,
    )

    assert args.key is not None  # MainArgs の __post_init__ で弾かれている
    return aalpy_dfa_to_cpp(
        dfa=dfa,
        alphabet=regex_property.alphabet,
        symbol_to_label=regex_property.symbol_to_label,
        namespace=args.namespace,
        key=args.key,
        add_sink_if_missing=False,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """
    path で受け取った property をもとに
    DFA を生成し、cpp ファイルを出力する

    オプションはコマンドライン引数で与える
    """

    args = parse_args(argv)

    if args.kind == "learn":
        result = _learn_cpp(args)
    elif args.kind == "regex":
        result = _regex_cpp(args)
    else:
        result = common_dfa_struct(namespace=args.namespace)

    print(result)
    return 0


if __name__ == "__main__":
    main()
