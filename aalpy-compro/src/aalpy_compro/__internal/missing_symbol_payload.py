from typing import ClassVar, Final, Self


class MissingSymbolPayload:
    """
    Regex クラスの _symbol の番兵
    """

    __slots__ = ()
    __instance: ClassVar[Self | None] = None

    def __new__(cls) -> Self:
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, _: dict[int, object]) -> Self:
        return self

    def __reduce__(self) -> tuple[type[Self], tuple[()]]:
        return (type(self), ())

    def __repr__(self) -> str:
        return "MISSING_SYMBOL_PAYLOAD"


MISSING_SYMBOL_PAYLOAD: Final = MissingSymbolPayload()
