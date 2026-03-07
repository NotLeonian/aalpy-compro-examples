import re


def allow_fullmatch(
    pattern: re.Pattern[str],
    string: str,
    exception: BaseException,
) -> None:
    """
    string が pattern に fullmatch しなければ
    exception を投げる関数

    pattern は必ず str ではなく
    re.Pattern[str] を投げる必要があることに注意
    """

    if pattern.fullmatch(string) is None:
        raise exception
