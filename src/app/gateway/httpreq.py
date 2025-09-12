from collections.abc import AsyncIterator
from typing import Any, Protocol


class IResponse(Protocol):
    @property
    def status_code(self) -> int: ...
    @property
    def text(self) -> str: ...
    @property
    def content(self) -> bytes: ...
    @property
    def url(self) -> Any: ...


class IHTTPRequest(Protocol):

    async def get(self, url: str) -> IResponse: ...
    async def get_many(
        self, urls: list[str], n: int
    ) -> AsyncIterator[list[IResponse]]: ...
