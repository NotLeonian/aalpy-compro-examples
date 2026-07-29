from abc import ABC, abstractmethod
from typing import Any

from .SUL import SUL

class Oracle(ABC):
    alphabet: list[Any]
    sul: SUL
    num_queries: int
    num_steps: int

    def __init__(self, alphabet: list[Any], sul: SUL) -> None: ...
    @abstractmethod
    def find_cex(
        self,
        hypothesis: Any,
    ) -> tuple[Any, ...] | list[Any] | None: ...
    def reset_hyp_and_sul(self, hypothesis: Any) -> None: ...
