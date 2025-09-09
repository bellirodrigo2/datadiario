from datetime import date
from typing import Protocol


class IGetLink(Protocol):
    async def __call__(self, date: date) -> list[str]: ...
