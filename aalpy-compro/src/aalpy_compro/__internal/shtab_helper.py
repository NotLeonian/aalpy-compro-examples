import argparse


def set_shtab_complete(action: argparse.Action, value: object) -> argparse.Action:
    setattr(action, "complete", value)
    return action
