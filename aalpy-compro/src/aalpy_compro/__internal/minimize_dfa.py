from collections import deque
from collections.abc import Hashable
from typing import TypeVar

from aalpy.automata import Dfa, DfaState

T = TypeVar("T", bound=Hashable)


def minimize_complete_dfa(
    state_setup: dict[str, tuple[bool, dict[T, str]]],
    *,
    alphabet: tuple[T, ...],
) -> Dfa[T]:
    """
    完全な遷移表を持つ DFA を最小化し、到達可能な状態のみを返す。

    最初の項目を初期状態とし、alphabet の順で最短の prefix を設定する。
    """
    if not state_setup:
        raise ValueError("`state_setup` must contain an initial state.")

    names = list(state_setup)
    indices = {name: index for index, name in enumerate(names)}
    accepting = [state_setup[name][0] for name in names]
    transitions = [
        [indices[state_setup[name][1][symbol]] for symbol in alphabet] for name in names
    ]
    blocks = [
        block
        for block in (
            {index for index, value in enumerate(accepting) if value},
            {index for index, value in enumerate(accepting) if not value},
        )
        if block
    ]
    block_of = [0] * len(names)
    for block_index, block in enumerate(blocks):
        for state_index in block:
            block_of[state_index] = block_index

    if len(blocks) > 1:
        predecessors: list[list[list[int]]] = [[[] for _ in names] for _ in alphabet]
        for source, row in enumerate(transitions):
            for symbol_index, target_index in enumerate(row):
                predecessors[symbol_index][target_index].append(source)

        smaller = min(range(len(blocks)), key=lambda index: len(blocks[index]))
        worklist = deque((smaller, index) for index in range(len(alphabet)))
        while worklist:
            splitter, symbol_index = worklist.popleft()
            incoming: dict[int, set[int]] = {}
            for target_index in blocks[splitter]:
                for source in predecessors[symbol_index][target_index]:
                    source_block = block_of[source]
                    intersecting = incoming.get(source_block)
                    if intersecting is None:
                        incoming[source_block] = {source}
                    else:
                        intersecting.add(source)

            for block_index, intersecting in incoming.items():
                block = blocks[block_index]
                if len(intersecting) == len(block):
                    continue

                if len(intersecting) <= len(block) // 2:
                    block.difference_update(intersecting)
                    smaller_block = intersecting
                else:
                    block.difference_update(intersecting)
                    smaller_block = block
                    blocks[block_index] = intersecting

                # 大きい側に元の番号を残すと、待機中の処理はそのまま使える。
                # 新たに小さい側だけを追加し、同じ遷移を調べる回数を抑える。
                new_index = len(blocks)
                blocks.append(smaller_block)
                for state_index in smaller_block:
                    block_of[state_index] = new_index
                worklist.extend((new_index, index) for index in range(len(alphabet)))

    representatives = [min(block) for block in blocks]
    initial_block = block_of[0]
    initial: DfaState[T] = DfaState(names[0], accepting[0])
    initial.prefix = ()
    states = [initial]
    by_block = {initial_block: initial}
    queue = deque([initial_block])
    while queue:
        block_index = queue.popleft()
        state = by_block[block_index]
        prefix = state.prefix
        assert prefix is not None
        representative = representatives[block_index]
        for symbol_index, symbol in enumerate(alphabet):
            target_block = block_of[transitions[representative][symbol_index]]
            target = by_block.get(target_block)
            if target is None:
                target_rep = representatives[target_block]
                target = DfaState(names[target_rep], accepting[target_rep])
                target.prefix = prefix + (symbol,)
                by_block[target_block] = target
                states.append(target)
                queue.append(target_block)
            state.transitions[symbol] = target

    return Dfa(initial, states)
