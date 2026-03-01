from collections import defaultdict, deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
import re

from aalpy.automata import Dfa
from aalpy.utils.FileHandler import save_automaton_to_file

import pydot


def dfa_to_dot_string[T](dfa: Dfa[T]) -> str:
    # AALpy では DFA の DOT を文字列として保存することが可能
    res = save_automaton_to_file(dfa, file_type="string")
    assert res is not None
    return res


def strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) < 2:
        return s
    if s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    if s[0] == "'" and s[-1] == "'":
        return s[1:-1]
    return s


__RE_INT = re.compile(r"([0-9]+)")


def natural_key(s: str) -> list[str | int]:
    # "q2" < "q10" にする
    return [int(t) if t.isdigit() else t for t in __RE_INT.split(s)]


@dataclass
class ParsedDfa:
    states: list[str]
    initial_state: str
    accepting: dict[str, bool]
    # (遷移前の状態, 入力文字) → 遷移後の状態
    trans: dict[tuple[str, str], str]


def parse_aalpy_dfa_dot(dot_text: str, *, drop_unreachable: bool = True) -> ParsedDfa:
    start0_str = "__start0"
    linefeed = "\n"
    linefeed_code = "\\n"

    graphs = pydot.graph_from_dot_data(dot_text)
    if not graphs:
        raise ValueError("DOT parse failed (no graphs).")
    g = graphs[0]

    states_set: set[str] = set()
    initial_state: str | None = None
    accepting: dict[str, bool] = {}
    trans: dict[tuple[str, str], str] = {}

    # Nodes
    for node in g.get_nodes():
        name = strip_quotes(node.get_name())
        if not name or name in (start0_str, linefeed, linefeed_code):
            continue
        states_set.add(name)
        attrs = node.get_attributes() or {}
        shape = attrs.get("shape", "")
        accepting[name] = "doublecircle" in shape

    # Edges
    for edge in g.get_edges():
        src = strip_quotes(str(edge.get_source()))
        dst = strip_quotes(str(edge.get_destination()))
        attrs = edge.get_attributes() or {}
        label = strip_quotes(attrs.get("label", ""))

        if src == start0_str:
            initial_state = dst
            states_set.add(dst)
            continue

        if (
            not src
            or not dst
            or src in (linefeed, linefeed_code)
            or dst in (linefeed, linefeed_code)
        ):
            continue

        states_set.add(src)
        states_set.add(dst)
        trans[(src, label)] = dst

    if initial_state is None:
        raise ValueError("DOT parse failed: missing __start0 -> <state> edge.")

    if drop_unreachable:
        adj = defaultdict(list)
        for (src, label), dst in trans.items():
            adj[src].append(dst)

        reachable = set([initial_state])
        q = deque([initial_state])
        while q:
            u = q.popleft()
            for v in adj.get(u, []):
                if v not in reachable:
                    reachable.add(v)
                    q.append(v)

        accepting = {s: accepting.get(s, False) for s in reachable}
        trans = {
            (src, lab): dst
            for (src, lab), dst in trans.items()
            if src in reachable and dst in reachable
        }

        states = sorted(reachable, key=natural_key)
    else:
        for s in states_set:
            accepting.setdefault(s, False)
        states = sorted(states_set, key=natural_key)

    return ParsedDfa(states, initial_state, accepting, trans)


def dot_to_cpp[T](
    *,
    dot_text: str,
    alphabet: Sequence[T],
    symbol_to_label: Callable[[T], str] = str,
    namespace: str = "learned_dfa",
    add_sink_if_missing: bool = True,
) -> str:
    """
    DOT 形式から C++ に変換 (0-based indexing)
    """

    parsed = parse_aalpy_dfa_dot(dot_text)

    labels = [symbol_to_label(a) for a in alphabet]
    label_to_col = {label: i for i, label in enumerate(labels)}
    if len(label_to_col) != len(labels):
        raise ValueError("alphabet has duplicate labels after symbol_to_label().")

    adj: dict[str, dict[str, str]] = {s: {} for s in parsed.states}
    for (src, label), dst in parsed.trans.items():
        adj[src][label] = dst

    idx = {s: i for i, s in enumerate(parsed.states)}
    n = len(parsed.states)
    k = len(labels)
    initial_state = idx[parsed.initial_state]

    trans_table: list[list[int]] = [[-1] * k for _ in range(n)]
    for i, src in enumerate(parsed.states):
        for label, j in label_to_col.items():
            _dst: str | None = adj.get(src, {}).get(label)
            if _dst is not None:
                trans_table[i][j] = idx[_dst]

    sink = None
    if add_sink_if_missing and any(
        trans_table[i][j] < 0 for i in range(n) for j in range(k)
    ):
        sink = n
        for i in range(n):
            for j in range(k):
                if trans_table[i][j] < 0:
                    trans_table[i][j] = sink
        trans_table.append([sink] * k)
        n += 1

    accepting = [True] * n
    for i, s in enumerate(parsed.states):
        accepting[i] = parsed.accepting.get(s, False)

    res: list[str] = []
    res.append(f"// States: {n}, Alphabet: {k}")
    res.append("// Symbol index mapping:")
    for j, lab in enumerate(labels):
        res.append(f"//   {j}: {lab}")
    res.append("")
    res.append(f"namespace {namespace} {{")
    res.append(f"static constexpr int N = {n};")
    res.append(f"static constexpr int SIGMA = {k};")
    res.append(f"static constexpr int INITIAL_STATE = {initial_state};")
    res.append(
        "static constexpr bool ACCEPTING[N] = { "
        + ", ".join(map(str, accepting))
        + " };"
    )
    res.append("static constexpr int TRANS[N][SIGMA] = {")
    for i in range(n):
        res.append("    { " + ", ".join(map(str, trans_table[i])) + " },")
    res.append("};")
    res.append("")
    res.append("template <class It>")
    res.append("bool accepts(It begin, It end) {")
    res.append("    int cur = INITIAL_STATE;")
    res.append("    for (auto it = begin; it != end; ++it) {")
    res.append("        const int label = *it;")
    res.append("        cur = TRANS[cur][label];")
    res.append("    }")
    res.append("    return ACCEPTING[cur];")
    res.append("}")
    res.append(f"}} // namespace {namespace}")

    return "\n".join(res)
