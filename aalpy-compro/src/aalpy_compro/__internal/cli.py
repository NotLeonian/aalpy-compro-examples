import argparse
import re
from collections.abc import Callable, Sequence

import shtab

from .eq_oracles import EqOracleList
from .fullmatch import validate_fullmatch_pattern
from .get_version import get_version
from .learn_dfa import (
    CliCexProcessingList,
    LearnAlgorithmList,
    LStarClosingStrategyList,
)
from .main_args import MainArgs
from .names import DIST_NAME
from .re_pattern import KEY_PATTERN, NAMESPACE_PATTERN
from .shtab_helper import set_shtab_complete


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    shtab.add_argument_to(parser, ["--print-completion"])

    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{DIST_NAME} {get_version()}",
    )

    parser.add_argument(
        "--kind",
        choices=["learn", "regex", "common"],
        help="Select \"learn\", \"regex\", or \"common\" (default: \"learn\").",
        default="learn",
    )
    set_shtab_complete(
        parser.add_argument(
            "--path",
            help="Path to .py file providing alphabet/accepts or alphabet/regex",
            default=None,
        ),
        shtab.FILE,
    )
    parser.add_argument(
        "--oracle",
        choices=EqOracleList,
        default=None,
        help=(
            "Base equivalence oracle. Optional when the property defines "
            "`eq_words`/`iter_eq_words`."
        ),
    )

    parser.add_argument(
        "--algorithm",
        choices=LearnAlgorithmList,
        default="kv",
    )

    parser.add_argument(
        "--namespace",
        type=parse_fullmatch_pattern(
            pattern=NAMESPACE_PATTERN,
            arg_name="namespace",
        ),
        help=f"--namespace must match /{NAMESPACE_PATTERN.pattern}/.",
        default="learned_dfa",
    )
    parser.add_argument(
        "--key",
        type=parse_fullmatch_pattern(
            pattern=KEY_PATTERN,
            arg_name="key",
        ),
        help="\n".join(
            [
                f"--key must match /{KEY_PATTERN.pattern}/.",
                "When --kind is \"learn\" or \"regex\", effectively required.",
                "Each name should be unique.",
            ]
        ),
        default=None,
    )

    # learning params
    parser.add_argument(
        "--cex-processing",
        choices=CliCexProcessingList,
        default="rs",
    )
    parser.add_argument("--max-rounds", type=int, default=None)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--print-level", type=int, default=2)

    # L* params
    parser.add_argument(
        "--closing-strategy",
        choices=LStarClosingStrategyList,
        default="shortest_first",
    )
    parser.add_argument(
        "--e-set-suffix-closed",
        action="store_true",
    )
    parser.add_argument(
        "--no-e-set-suffix-closed",
        dest="e_set_suffix_closed",
        action="store_false",
    )
    parser.add_argument(
        "--all-prefixes-in-obs-table",
        action="store_true",
    )
    parser.add_argument(
        "--no-all-prefixes-in-obs-table",
        dest="all_prefixes_in_obs_table",
        action="store_false",
    )

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
    parser.add_argument(
        "--no-depth-first",
        dest="depth_first",
        action="store_false",
    )

    parser.set_defaults(
        depth_first=True,
        e_set_suffix_closed=False,
        all_prefixes_in_obs_table=True,
    )

    return parser


def parse_args(argv: Sequence[str] | None = None) -> MainArgs:
    return MainArgs(**vars(build_parser().parse_args(argv)))
