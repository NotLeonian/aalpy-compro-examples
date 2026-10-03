"""Run with the same interpreter and PYTHONPATH for each revision being compared.

Example: python aalpy-compro/benchmarks/benchmark_performance.py --repeat 5
Use --memory for an additional, separately traced run of each selected case.
Regex construction is outside the timed region; compilation includes minimization.
The prefix case includes one cold query followed by 39 queries of the same word.
The short-prefix case covers every binary word of length eight, repeated 20 times.
"""

import argparse
import gc
import json
import platform
import statistics
import time
import tracemalloc
from collections.abc import Callable, Iterator
from itertools import product

import aalpy_compro
from aalpy_compro import Regex
from aalpy_compro.__internal.learn_dfa import (
    KVLearnConfig,
    LearnConfigSpec,
    LStarLearnConfig,
    learn_dfa,
)
from aalpy_compro.__internal.prefix_accepting_sul import PrefixAcceptingSUL
from aalpy_compro.__internal.regex_to_dfa import regex_to_dfa


def compilation(regex: Regex[int], alphabet: tuple[int, ...]) -> Callable[[], int]:
    def run() -> int:
        return len(regex_to_dfa(regex=regex, alphabet=alphabet).states)

    return run


def learning(config: LearnConfigSpec) -> Callable[[], int]:
    def accepts(word: tuple[int, ...]) -> bool:
        return len(word) % 127 == 0

    def words() -> Iterator[tuple[int, ...]]:
        for length in range(254):
            yield (0,) * length

    def run() -> int:
        dfa = learn_dfa(
            alphabet=(0,),
            accepts=accepts,
            oracle_spec=None,
            learn_config=config,
            fixed_eq_word_factory=words,
        )
        assert len(dfa.states) == 127
        return len(dfa.states)

    return run


def prefix_queries(
    words: tuple[tuple[int, ...], ...], repetitions: int, expected_calls: int
) -> Callable[[], int]:
    def run() -> int:
        calls = 0

        def accepts(prefix: tuple[int, ...]) -> bool:
            nonlocal calls
            calls += 1
            return len(prefix) % 7 == 0

        sul = PrefixAcceptingSUL(accepts)
        for _ in range(repetitions):
            for word in words:
                sul.query(word)
        assert calls == expected_calls
        return calls

    return run


def workloads() -> dict[str, Callable[[], int]]:
    optional = Regex.symbol(0).optional()
    branches = [Regex.word((i, (i + 1) % 32)).star() for i in range(32)]
    expressions: dict[str, tuple[Regex[int], tuple[int, ...]]] = {
        "regex_literal": (Regex.word((0,) * 400), (0, 1)),
        "regex_optional": (optional.concat(*([optional] * 399)), (0, 1)),
        "regex_suffix": (
            (Regex[int].dot().star() + Regex.symbol(0)).concat(
                *[Regex[int].dot() for _ in range(9)]
            ),
            (0, 1),
        ),
        "regex_wide_alphabet": (branches[0].union(*branches[1:]), tuple(range(32))),
    }
    cases: dict[str, Callable[[], int]] = {}
    for name, (regex, alphabet) in expressions.items():
        cases[name] = compilation(regex, alphabet)

    cases["prefix_queries"] = prefix_queries(((0, 1) * 750,), 40, 1500)
    cases["prefix_short_queries"] = prefix_queries(
        tuple(product((0, 1), repeat=8)), 20, 510
    )
    cases["learning_kv"] = learning(KVLearnConfig(print_level=0))
    cases["learning_lstar"] = learning(LStarLearnConfig(print_level=0))
    return cases


def main() -> None:
    cases = workloads()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--case", choices=list(cases), action="append")
    parser.add_argument("--memory", action="store_true")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")

    results: list[dict[str, object]] = []
    for name in args.case or cases:
        run = cases[name]
        elapsed: list[float] = []
        result: int | None = None
        for _ in range(args.repeat):
            gc.collect()
            start = time.perf_counter()
            result = run()
            elapsed.append(time.perf_counter() - start)
        assert result is not None
        row: dict[str, object] = {
            "case": name,
            "median_seconds": statistics.median(elapsed),
            "result": result,
        }
        if args.memory:
            gc.collect()
            tracemalloc.start()
            run()
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            row["peak_bytes"] = peak
        results.append(row)

    print(
        json.dumps(
            {
                "python": platform.python_version(),
                "package": aalpy_compro.__file__,
                "repeat": args.repeat,
                "results": results,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
