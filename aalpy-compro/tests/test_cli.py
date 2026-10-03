import io
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from aalpy_compro.main import main


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.learning_property = self.write_property(
            "learning.py",
            """
            from itertools import product

            alphabet = [0, 1]

            def accepts(word):
                return bool(word) and word[-1] == 1

            eq_words = [word for n in range(4) for word in product(alphabet, repeat=n)]
            """,
        )

    def write_property(self, name: str, source: str) -> str:
        path = self.directory / name
        path.write_text(textwrap.dedent(source), encoding="utf-8")
        return str(path)

    def invoke(self, *args: str) -> int:
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        with (
            patch("sys.argv", ["aalpy-compro", *args]),
            redirect_stdout(self.stdout),
            redirect_stderr(self.stderr),
        ):
            return main()

    def learn(self, *args: str) -> int:
        return self.invoke(
            "--path",
            self.learning_property,
            "--key",
            "last_one",
            "--print-level",
            "0",
            *args,
        )

    def assert_last_one_dfa(self, namespace: str = "learned_dfa") -> None:
        output = self.stdout.getvalue()
        self.assertTrue(output.startswith("#include <array>\n"))
        self.assertIn(f"namespace {namespace}_last_one {{", output)
        self.assertIn("// States: 2, Alphabet: 2", output)
        self.assertIn("ACCEPTING = {{\n    0, 1\n}};", output)
        self.assertIn("TRANS = {{\n    {{0, 1}},\n    {{0, 1}},\n}};", output)
        self.assertIn(
            f'{namespace}::dfas().register_dfa(INITIAL_STATE, ACCEPTING, TRANS, "last_one");',
            output,
        )

    def test_common_does_not_require_key_or_property(self) -> None:
        for options, namespace in [
            ([], "learned_dfa"),
            (["--namespace", "custom"], "custom"),
        ]:
            with self.subTest(namespace=namespace):
                self.assertEqual(self.invoke("--kind", "common", *options), 0)
                self.assertIn(f"namespace {namespace} {{", self.stdout.getvalue())
                self.assertIn("class DFA {", self.stdout.getvalue())
                self.assertIn("class DFAs {", self.stdout.getvalue())
                self.assertEqual(self.stderr.getvalue(), "")

    def test_explicit_arguments_override_process_arguments(self) -> None:
        with (
            patch("sys.argv", ["aalpy-compro", "--invalid-option"]),
            redirect_stdout(self.stdout),
            redirect_stderr(self.stderr),
        ):
            self.assertEqual(main(["--kind", "common", "--namespace", "custom"]), 0)
        self.assertIn("namespace custom {", self.stdout.getvalue())
        self.assertEqual(self.stderr.getvalue(), "")

    def test_regex_loads_property_and_preserves_alphabet_order_and_labels(self) -> None:
        path = self.write_property(
            "regex.py",
            """
            from aalpy_compro import Regex

            alphabet = [1, 0]
            regex = Regex.dot().star() + Regex.symbol(1)

            def symbol_to_label(symbol):
                return f"bit_{symbol}"
            """,
        )
        self.assertEqual(
            self.invoke(
                "--kind",
                "regex",
                "--path",
                path,
                "--key",
                "last_one",
                "--namespace",
                "custom",
            ),
            0,
        )
        output = self.stdout.getvalue()
        self.assertIn("namespace custom_last_one {", output)
        self.assertIn("//   0: bit_1\n//   1: bit_0", output)
        self.assertIn("ACCEPTING = {{\n    0, 1\n}};", output)
        self.assertIn("TRANS = {{\n    {{1, 0}},\n    {{1, 0}},\n}};", output)
        self.assertEqual(self.stderr.getvalue(), "")

    def test_learning_defaults_match_explicit_defaults(self) -> None:
        self.assertEqual(self.learn(), 0)
        expected = self.stdout.getvalue()
        self.assert_last_one_dfa()
        self.assertEqual(self.stderr.getvalue(), "")
        self.assertEqual(
            self.learn(
                "--kind",
                "learn",
                "--algorithm",
                "kv",
                "--namespace",
                "learned_dfa",
                "--cex-processing",
                "rs",
                "--closing-strategy",
                "shortest_first",
                "--no-e-set-suffix-closed",
                "--all-prefixes-in-obs-table",
                "--min-length",
                "1",
                "--expected-length",
                "10",
                "--num-tests",
                "1000",
                "--walks-per-state",
                "25",
                "--walk-len",
                "12",
                "--depth-first",
            ),
            0,
        )
        self.assertEqual(self.stdout.getvalue(), expected)
        self.assertEqual(self.stderr.getvalue(), "")

    def test_both_algorithms_learn_from_custom_equivalence_words(self) -> None:
        for algorithm in ("kv", "lstar"):
            with self.subTest(algorithm=algorithm):
                self.assertEqual(self.learn("--algorithm", algorithm), 0)
                self.assert_last_one_dfa()
                self.assertEqual(self.stderr.getvalue(), "")

    def test_lstar_accepts_its_specific_options(self) -> None:
        self.assertEqual(
            self.learn(
                "--algorithm",
                "lstar",
                "--cex-processing",
                "none",
                "--closing-strategy",
                "longest_first",
                "--e-set-suffix-closed",
                "--no-all-prefixes-in-obs-table",
                "--no-cache",
            ),
            0,
        )
        self.assert_last_one_dfa()

    def test_non_default_base_oracle_options_warn_without_base_oracle(self) -> None:
        for options in [
            ("--max-states", "2"),
            ("--min-length", "2"),
            ("--expected-length", "11"),
            ("--num-tests", "1"),
            ("--walks-per-state", "1"),
            ("--walk-len", "1"),
            ("--max-tests", "1"),
            ("--no-depth-first",),
        ]:
            with self.subTest(options=options):
                self.assertEqual(self.learn(*options), 0)
                self.assert_last_one_dfa()
                self.assertEqual(
                    self.stderr.getvalue(),
                    "Warning: base-oracle-specific options require --oracle.\n",
                )

    def test_base_oracle_can_be_combined_with_custom_equivalence_words(self) -> None:
        for options in [
            ("--oracle", "wp", "--max-states", "2"),
            ("--oracle", "random_wp", "--num-tests", "1"),
            ("--oracle", "state_prefix", "--walks-per-state", "1", "--walk-len", "1"),
        ]:
            with self.subTest(options=options):
                self.assertEqual(self.learn(*options), 0)
                self.assert_last_one_dfa()
                self.assertEqual(self.stderr.getvalue(), "")

    def test_missing_key_is_reported_before_missing_path(self) -> None:
        for kind in ("learn", "regex"):
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError) as raised:
                    self.invoke("--kind", kind)
                self.assertEqual(
                    str(raised.exception),
                    f'When --kind is "{kind}", --key is required.',
                )

    def test_missing_path_is_reported_before_oracle_constraints(self) -> None:
        for kind in ("learn", "regex"):
            with self.subTest(kind=kind):
                with self.assertRaises(SystemExit) as raised:
                    self.invoke("--kind", kind, "--key", "sample", "--oracle", "wp")
                self.assertEqual(
                    raised.exception.code, f"--kind {kind} requires --path."
                )

    def test_learning_requires_equivalence_oracle_source(self) -> None:
        path = self.write_property(
            "without_oracle.py", "alphabet = [0]\ndef accepts(word): return True\n"
        )
        with self.assertRaises(SystemExit) as raised:
            self.invoke("--path", path, "--key", "sample", "--max-states", "2")
        self.assertEqual(
            raised.exception.code,
            "--kind learn requires at least one equivalence oracle source: "
            "--oracle, `eq_words`/`iter_eq_words`.",
        )
        self.assertEqual(self.stderr.getvalue(), "")

    def test_wp_requires_max_states(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            self.learn("--oracle", "wp")
        self.assertEqual(raised.exception.code, "--oracle wp requires --max-states.")

    def test_kv_rejects_lstar_only_options(self) -> None:
        for options, message in [
            (("--closing-strategy", "longest_first"), "--closing-strategy"),
            (("--e-set-suffix-closed",), "--e-set-suffix-closed"),
            (("--no-all-prefixes-in-obs-table",), "--no-all-prefixes-in-obs-table"),
        ]:
            with self.subTest(options=options):
                with self.assertRaises(SystemExit) as raised:
                    self.learn(*options)
                self.assertEqual(
                    raised.exception.code,
                    f"{message} is only valid with --algorithm lstar.",
                )
        for strategy in ("none", "longest_prefix"):
            with self.subTest(strategy=strategy):
                with self.assertRaises(SystemExit) as raised:
                    self.learn("--cex-processing", strategy)
                self.assertEqual(
                    raised.exception.code,
                    f"--algorithm kv does not support --cex-processing {strategy!r}.",
                )

    def test_argument_parser_rejects_invalid_identifiers_and_choices(self) -> None:
        for option, value in [
            ("--namespace", "bad-name"),
            ("--key", "bad-key"),
            ("--kind", "unknown"),
            ("--oracle", "unknown"),
            ("--algorithm", "unknown"),
        ]:
            with self.subTest(option=option):
                with self.assertRaises(SystemExit) as raised:
                    self.invoke("--kind", "common", option, value)
                self.assertEqual(raised.exception.code, 2)
                self.assertIn(option, self.stderr.getvalue())
                self.assertEqual(self.stdout.getvalue(), "")

    def test_help_version_and_completion_exit_before_key_validation(self) -> None:
        for options, expected in [
            (("--help",), "--kind"),
            (("--version",), "aalpy-compro "),
            (("--print-completion", "bash"), "--kind"),
        ]:
            with self.subTest(options=options):
                with self.assertRaises(SystemExit) as raised:
                    self.invoke(*options)
                self.assertEqual(raised.exception.code, 0)
                self.assertIn(expected, self.stdout.getvalue())
                self.assertEqual(self.stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
