import tempfile
import textwrap
import unittest
from pathlib import Path

from aalpy_compro.__internal.learning_property import load_learning_property
from aalpy_compro.__internal.regex_property import load_regex_property
from aalpy_compro.regex import ComplementRegex, Regex


class PropertyLoadingTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.path = Path(temporary_directory.name) / "property.py"

    def write_property(self, source: str) -> str:
        self.path.write_text(textwrap.dedent(source), encoding="utf-8")
        return str(self.path)

    def test_required_attributes_are_checked_in_order(self) -> None:
        for loader, required in (
            (load_learning_property, "accepts"),
            (load_regex_property, "regex"),
        ):
            for source, missing in (("", "alphabet"), ("alphabet = []", required)):
                with self.subTest(loader=loader.__name__, missing=missing):
                    path = self.write_property(source)
                    with self.assertRaises(ValueError) as error:
                        loader(path)
                    self.assertEqual(
                        str(error.exception), f"`{missing}` must be defined in {path}."
                    )

    def test_unsupported_file_extension_preserves_error(self) -> None:
        path = str(self.path.with_suffix(".txt"))
        for loader in (load_learning_property, load_regex_property):
            with self.subTest(loader=loader.__name__):
                with self.assertRaises(ValueError) as error:
                    loader(path)
                self.assertEqual(
                    str(error.exception), f"Cannot load property from {path}."
                )

    def test_execution_errors_propagate(self) -> None:
        path = self.write_property('raise RuntimeError("property failed")')
        for loader in (load_learning_property, load_regex_property):
            with (
                self.subTest(loader=loader.__name__),
                self.assertRaisesRegex(RuntimeError, "^property failed$"),
            ):
                loader(path)

    def test_each_load_executes_a_fresh_module_with_the_original_name(self) -> None:
        path = self.write_property(
            """
            from aalpy_compro.regex import Regex
            alphabet = [0, 1]
            accepts = lambda word: word == (1,)
            regex = Regex.symbol(1)
            calls = 0
            def symbol_to_label(symbol):
                global calls
                calls += 1
                return f"{__name__}:{calls}:{symbol}"
            """
        )
        for loader, module_name in (
            (load_learning_property, "learning_property"),
            (load_regex_property, "regex_property"),
        ):
            with self.subTest(loader=loader.__name__):
                first = loader(path)
                self.assertEqual(first.alphabet, (0, 1))
                self.assertEqual(first.symbol_to_label(1), f"{module_name}:1:1")
                self.assertEqual(first.symbol_to_label(1), f"{module_name}:2:1")
                second = loader(path)
                self.assertEqual(second.symbol_to_label(1), f"{module_name}:1:1")

    def test_validation_order_is_preserved(self) -> None:
        cases = (
            (
                load_learning_property,
                "alphabet = 0\naccepts = 0\nsymbol_to_label = 0",
                "`accepts` must be callable in {path}.",
            ),
            (
                load_regex_property,
                "alphabet = 0\nregex = 0\nsymbol_to_label = 0",
                (
                    "`regex` must be an instance of `aalpy_compro.regex.Regex` "
                    "or `aalpy_compro.regex.ComplementRegex` in {path}."
                ),
            ),
        )
        for loader, source, message in cases:
            with self.subTest(loader=loader.__name__):
                path = self.write_property(source)
                with self.assertRaises(TypeError) as error:
                    loader(path)
                self.assertEqual(str(error.exception), message.format(path=path))

        for loader in (load_learning_property, load_regex_property):
            for label_definition, message in (
                ("symbol_to_label = 0", "`symbol_to_label` must be callable"),
                ("", "`alphabet` must be a non-string iterable"),
            ):
                with self.subTest(loader=loader.__name__, label=label_definition):
                    path = self.write_property(
                        "from aalpy_compro.regex import Regex\n"
                        "alphabet = 0\naccepts = lambda word: True\n"
                        f"regex = Regex.symbol(1)\n{label_definition}\n"
                    )
                    with self.assertRaises(TypeError) as error:
                        loader(path)
                    self.assertEqual(str(error.exception), f"{message} in {path}.")

    def test_default_labels_and_complement_regex_are_preserved(self) -> None:
        path = self.write_property(
            """
            from aalpy_compro.regex import Regex
            alphabet = [1]
            accepts = lambda word: word == (1,)
            regex = ~Regex.symbol(1)
            """
        )
        learning_property = load_learning_property(path)
        self.assertIs(learning_property.symbol_to_label, str)
        self.assertTrue(learning_property.accepts((1,)))
        self.assertFalse(learning_property.accepts(()))
        self.assertIsNone(learning_property.fixed_eq_word_factory)
        regex_property = load_regex_property(path)
        self.assertIs(regex_property.symbol_to_label, str)
        self.assertIsInstance(regex_property.regex, ComplementRegex)
        self.assertEqual(regex_property.regex, ~Regex.symbol(1))

    def test_cyclic_regex_is_rejected(self) -> None:
        path = self.write_property(
            """
            from aalpy_compro.regex import Regex
            alphabet = [1]
            regex = Regex.symbol(1).star()
            object.__setattr__(regex, "_parts", (regex,))
            """
        )
        with self.assertRaisesRegex(ValueError, r"^Cyclic Regex is not supported\.$"):
            load_regex_property(path)

    def test_equivalence_word_factory_is_lazy_and_reusable(self) -> None:
        path = self.write_property(
            """
            alphabet = [1, 2]
            calls = 0
            accepts = lambda word: calls == 0
            def iter_eq_words():
                global calls
                calls += 1
                return [[], [calls]]
            """
        )
        property_ = load_learning_property(path)
        self.assertTrue(property_.accepts(()))
        factory = property_.fixed_eq_word_factory
        assert factory is not None
        self.assertEqual(list(factory()), [(), (1,)])
        self.assertEqual(list(factory()), [(), (2,)])

    def test_fixed_equivalence_words_can_be_reiterated(self) -> None:
        path = self.write_property(
            """
            alphabet = [1]
            accepts = lambda word: True
            eq_words = [[], [1]]
            """
        )
        factory = load_learning_property(path).fixed_eq_word_factory
        assert factory is not None
        self.assertEqual(list(factory()), [(), (1,)])
        self.assertEqual(list(factory()), [(), (1,)])

    def test_equivalence_word_errors_keep_their_timing(self) -> None:
        prefix = "alphabet = [1]\naccepts = lambda word: True\n"
        path = self.write_property(prefix + "eq_words = []\niter_eq_words = lambda: []")
        with self.assertRaises(ValueError) as error:
            load_learning_property(path)
        self.assertEqual(
            str(error.exception),
            "Define at most one of `eq_words` and `iter_eq_words`.",
        )

        path = self.write_property(prefix + "eq_words = iter([[]])")
        with self.assertRaises(ValueError) as error:
            load_learning_property(path)
        self.assertEqual(
            str(error.exception),
            "`eq_words` must be re-iterable. Use `iter_eq_words` for generators.",
        )

        path = self.write_property(prefix + "iter_eq_words = lambda: 1")
        factory = load_learning_property(path).fixed_eq_word_factory
        assert factory is not None
        with self.assertRaises(TypeError) as type_error:
            factory()
        self.assertEqual(
            str(type_error.exception),
            "`iter_eq_words()` must return a non-string iterable of non-string iterables.",
        )

        path = self.write_property(prefix + "eq_words = [[[]]]")
        factory = load_learning_property(path).fixed_eq_word_factory
        assert factory is not None
        words = factory()
        with self.assertRaises(TypeError) as type_error:
            list(words)
        self.assertEqual(
            str(type_error.exception),
            "`eq_words` contains a word at index 0 whose symbols must all be hashable.",
        )


if __name__ == "__main__":
    unittest.main()
