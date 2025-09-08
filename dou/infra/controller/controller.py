from typing import Optional, Protocol


class IController(Protocol):

    def start(self, args: Optional[list[str]] = None): ...
    def get_registered_commands(self) -> list[str]: ...
