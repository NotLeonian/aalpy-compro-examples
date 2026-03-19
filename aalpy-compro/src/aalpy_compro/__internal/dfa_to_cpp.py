from collections import deque
from collections.abc import Callable, Hashable, Sequence
from typing import TypeVar

from aalpy.automata import Dfa, DfaState

from .validation_for_aalpy import validate_aalpy_alphabet

T = TypeVar("T", bound=Hashable)


def validated_labels(
    *,
    alphabet: Sequence[T],
    symbol_to_label: Callable[[T], str],
) -> list[str]:
    labels = [symbol_to_label(a) for a in alphabet]
    label_to_col = {label: i for i, label in enumerate(labels)}
    if len(label_to_col) != len(labels):
        raise ValueError("`alphabet` has duplicate labels after `symbol_to_label`.")
    return labels


def render_cpp(
    *,
    namespace: str,
    key: str,
    labels: list[str],
    initial_state: int,
    accepting: list[int],
    trans_table: list[list[int]],
) -> str:
    n = len(trans_table)
    sigma = len(labels)

    res: list[str] = []
    res.append("#include <array>")
    res.append("")
    res.append(f"namespace {namespace}_{key} {{")
    res.append(f"// States: {n}, Alphabet: {sigma}")
    res.append("// Symbol index mapping:")
    for j, label in enumerate(labels):
        res.append(f"//   {j}: {label}")
    res.append("")
    res.append(f"inline constexpr int N = {n};")
    res.append(f"inline constexpr int SIGMA = {sigma};")
    res.append(f"inline constexpr int INITIAL_STATE = {initial_state};")
    res.append("")
    res.append("inline constexpr std::array<unsigned char, N> ACCEPTING = {{")
    res.append(f"    {', '.join(map(str, accepting))}")
    res.append("}};")
    res.append("")
    res.append("inline constexpr std::array<std::array<int, SIGMA>, N> TRANS = {{")
    for row in trans_table:
        res.append(f"    {{{{{', '.join(map(str, row))}}}}},")
    res.append("}};")
    res.append("")
    res.append(f"static const int __{namespace}_register_{key} = [] {{")
    res.append(
        f'    {namespace}::dfas().register_dfa(INITIAL_STATE, ACCEPTING, TRANS, "{key}");'
    )
    res.append("    return 0;")
    res.append("}();")
    res.append(f"}} // namespace {namespace}_{key}")
    res.append("")

    return "\n".join(res)


def aalpy_dfa_to_cpp(
    *,
    dfa: Dfa[T],
    alphabet: Sequence[T],
    symbol_to_label: Callable[[T], str] = str,
    namespace: str = "learned_dfa",
    key: str = "",
    add_sink_if_missing: bool = True,
) -> str:
    """
    AALpy の Dfa オブジェクトを C++ に変換する
    (0-based indexing)
    """

    labels = validated_labels(
        alphabet=alphabet,
        symbol_to_label=symbol_to_label,
    )

    alphabet_tuple, alphabet_set = validate_aalpy_alphabet(alphabet)

    order: list[DfaState[T]] = []
    visited: set[DfaState[T]] = {dfa.initial_state}
    q: deque[DfaState[T]] = deque([dfa.initial_state])

    while q:
        cur_state = q.popleft()
        order.append(cur_state)

        extra_symbols = [
            symbol for symbol in cur_state.transitions if symbol not in alphabet_set
        ]
        if extra_symbols:
            raise ValueError(
                "`dfa` has transitions labeled by symbols outside `alphabet`: "
                f"{[repr(symbol) for symbol in extra_symbols]}"
            )

        for symbol in alphabet_tuple:
            dst = cur_state.transitions.get(symbol)
            if dst is None or dst in visited:
                continue
            visited.add(dst)
            q.append(dst)

    idx = {s: i for i, s in enumerate(order)}
    n = len(order)
    sigma = len(labels)

    trans_table: list[list[int]] = [[-1] * sigma for _ in range(n)]
    for i, src in enumerate(order):
        for j, label in enumerate(alphabet_tuple):
            dst = src.transitions.get(label)
            # dead 状態 (sink) への遷移が省略されている可能性がある
            if dst is not None:
                trans_table[i][j] = idx[dst]

    sink = None
    if add_sink_if_missing and any(
        trans_table[i][j] < 0 for i in range(n) for j in range(sigma)
    ):
        sink = n
        for row in trans_table:
            for j, dst in enumerate(row):
                if dst < 0:
                    row[j] = sink
        trans_table.append([sink] * sigma)
        n += 1

    accepting = [1 if state.is_accepting else 0 for state in order]
    if sink is not None:
        accepting.append(0)

    return render_cpp(
        trans_table=trans_table,
        accepting=accepting,
        labels=labels,
        initial_state=0,  # initial_state は 0
        namespace=namespace,
        key=key,
    )
