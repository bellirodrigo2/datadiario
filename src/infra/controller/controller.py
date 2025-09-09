from typing import Any, Protocol


class IController(Protocol):

    def start(self, **kwargs: Any) -> int: ...
    def get_registered_commands(self) -> list[str]: ...
