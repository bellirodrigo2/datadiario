from datetime import date
from typing import Any, AsyncGenerator, Protocol


class IGetLink(Protocol):
    async def __call__(self, date: date) -> list[str]: ...


class IGetContent(Protocol):
    async def __call__(
        self, link: list[str]
    ) -> AsyncGenerator[list[dict[str, Any]], None]: ...
