import argparse
from typing import Protocol, cast


class _ShtabCompletable(Protocol):
    complete: object


def set_shtab_complete(action: argparse.Action, value: object) -> argparse.Action:
    cast(_ShtabCompletable, action).complete = value
    return action
