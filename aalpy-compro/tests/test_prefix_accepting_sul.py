import unittest
from collections.abc import Hashable
from itertools import product
from typing import cast
from unittest.mock import Mock, call

from aalpy.base.SUL import CacheSUL
from aalpy_compro.__internal.prefix_accepting_sul import PrefixAcceptingSUL


class CountingSymbol:
    def __init__(self, value: str) -> None:
        self.value = value
        self.hash_calls = 0

    def __hash__(self) -> int:
        self.hash_calls += 1
        return 0

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CountingSymbol) and self.value == other.value


class PrefixAcceptingSULTests(unittest.TestCase):
    def test_queries_cache_each_distinct_prefix_including_false(self) -> None:
        calls: list[tuple[int, ...]] = []

        def accepts(word: tuple[int, ...]) -> bool:
            calls.append(word)
            return word.count(1) % 2 == 0

        sul = PrefixAcceptingSUL(accepts)
        words = [word for length in range(6) for word in product((0, 1), repeat=length)]
        for _ in range(2):
            for word in words:
                expected = [
                    word[:length].count(1) % 2 == 0
                    for length in range(1, len(word) + 1)
                ] or [True]
                self.assertEqual(sul.query(word), expected)

        self.assertCountEqual(calls, words)

    def test_none_observes_current_prefix_and_pre_resets_it(self) -> None:
        calls: list[tuple[str, ...]] = []

        def accepts(word: tuple[str, ...]) -> bool:
            calls.append(word)
            return bool(word)

        sul = PrefixAcceptingSUL(accepts)
        self.assertFalse(sul.step(None))
        self.assertFalse(sul.step(None))
        self.assertTrue(sul.step("a"))
        self.assertTrue(sul.step(None))
        self.assertEqual(sul.prefix, ["a"])
        sul.post()
        self.assertTrue(sul.step(None))
        sul.pre()
        self.assertEqual(sul.prefix, [])
        self.assertFalse(sul.step(None))
        self.assertTrue(sul.step("a"))
        self.assertEqual(calls, [(), ("a",)])

    def test_none_callback_result_remains_cached(self) -> None:
        calls: list[tuple[str, ...]] = []

        def accepts(word: tuple[str, ...]) -> bool:
            calls.append(word)
            return cast(bool, None)

        sul = PrefixAcceptingSUL(accepts)
        self.assertEqual(sul.query(("a",)), [None])
        self.assertIsNone(sul.step(None))
        self.assertEqual(sul.query(("a",)), [None])
        self.assertEqual(calls, [("a",)])

    def test_callback_exception_is_retried_without_losing_prefix(self) -> None:
        for error in (RuntimeError("callback failed"), TypeError("callback failed")):
            with self.subTest(error=type(error)):
                accepts = Mock(side_effect=[error, True, True])
                sul = PrefixAcceptingSUL[str](accepts)
                with self.assertRaises(type(error)) as caught:
                    sul.step("a")
                self.assertIs(caught.exception, error)
                self.assertEqual(sul.prefix, ["a"])
                self.assertTrue(sul.step(None))
                self.assertTrue(sul.step("b"))
                self.assertEqual(
                    accepts.call_args_list,
                    [call(("a",)), call(("a",)), call(("a", "b"))],
                )
                self.assertEqual(sul.query(("a", "b")), [True, True])
                self.assertEqual(accepts.call_count, 3)

    def test_callback_exception_allows_advancing_to_the_next_prefix(self) -> None:
        calls: list[tuple[str, ...]] = []

        def accepts(word: tuple[str, ...]) -> bool:
            calls.append(word)
            if len(calls) == 1:
                raise RuntimeError("callback failed")
            return True

        sul = PrefixAcceptingSUL(accepts)
        with self.assertRaises(RuntimeError):
            sul.step("a")
        self.assertTrue(sul.step("b"))
        self.assertEqual(calls, [("a",), ("a", "b")])
        self.assertEqual(sul.query(("a", "b")), [True, True])
        self.assertEqual(calls, [("a",), ("a", "b"), ("a",)])

    def test_unhashable_input_remains_invalid_until_pre(self) -> None:
        calls: list[tuple[Hashable, ...]] = []

        def accepts(word: tuple[Hashable, ...]) -> bool:
            calls.append(word)
            return True

        sul = PrefixAcceptingSUL(accepts)
        self.assertTrue(sul.step("a"))
        for symbol in (cast(Hashable, []), None, "b"):
            with self.assertRaisesRegex(TypeError, "Input symbols must be hashable"):
                sul.step(symbol)
        self.assertEqual(sul.prefix, ["a", [], "b"])
        self.assertEqual(calls, [("a",)])
        sul.pre()
        self.assertTrue(sul.step("b"))
        self.assertEqual(calls, [("a",), ("b",)])

    def test_hash_collisions_and_equal_symbols_keep_word_semantics(self) -> None:
        calls: list[tuple[CountingSymbol, ...]] = []

        def accepts(word: tuple[CountingSymbol, ...]) -> bool:
            calls.append(word)
            return word[-1].value == "a"

        sul = PrefixAcceptingSUL(accepts)
        for _ in range(2):
            self.assertEqual(
                sul.query((CountingSymbol("a"), CountingSymbol("b"))), [True, False]
            )
            self.assertEqual(
                sul.query((CountingSymbol("b"), CountingSymbol("a"))), [False, True]
            )
        self.assertEqual(len(calls), 4)

    def test_cached_walk_hashes_symbols_linearly(self) -> None:
        for length in (16, 256):
            with self.subTest(length=length):
                symbol = CountingSymbol("a")
                sul = PrefixAcceptingSUL[CountingSymbol](lambda _: True)
                word = (symbol,) * length
                sul.query(word)
                symbol.hash_calls = 0
                self.assertEqual(sul.query(word), [True] * length)
                self.assertLessEqual(symbol.hash_calls, 2 * length)

    def test_query_and_step_statistics_are_unchanged(self) -> None:
        sul = PrefixAcceptingSUL[str](lambda _: True)
        sul.query(("a", "b"))
        sul.query(("a", "b"))
        sul.query(())
        sul.pre()
        sul.step("a")
        self.assertEqual(sul.num_queries, 3)
        self.assertEqual(sul.num_steps, 4)
        self.assertEqual(sul.num_cached_queries, 0)

    def test_aalpy_cache_reuses_results_during_step_walks(self) -> None:
        calls: list[tuple[str, ...]] = []

        def accepts(word: tuple[str, ...]) -> bool:
            calls.append(word)
            return len(word) % 2 == 0

        sul = PrefixAcceptingSUL(accepts)
        cached = CacheSUL(sul)
        self.assertEqual(list(cached.query(("a", "b"))), [False, True])
        self.assertEqual(list(cached.query(("a", "b"))), [False, True])
        cached.pre()
        self.assertFalse(cached.step("a"))
        self.assertTrue(cached.step("b"))
        self.assertFalse(cached.step("c"))
        cached.post()
        self.assertEqual(calls, [("a",), ("a", "b"), ("a", "b", "c")])
        self.assertEqual(sul.num_queries, 1)
        self.assertEqual(cached.num_queries, 1)
        self.assertEqual(cached.num_cached_queries, 1)


if __name__ == "__main__":
    unittest.main()
