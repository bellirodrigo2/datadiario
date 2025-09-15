import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from ...app.gateway.httpreq import IHTTPRequest, IResponse


def sublist(lista: list[Any], n: int):
    return [lista[i : i + n] for i in range(0, len(lista), n)]


logger = logging.getLogger("httpx")
logger.setLevel(logging.CRITICAL)


@dataclass
class HttpxErrorResponse(IResponse):
    _url: str
    _error: BaseException
    _response_text: Optional[str] = None

    @property
    def text(self) -> str:
        return str(self._error)

    @property
    def content(self) -> bytes:
        return self.text.encode("utf-8")

    @property
    def status_code(self) -> int:
        return 0

    @property
    def url(self) -> str:
        return self._url

    @property
    def raw_url(self) -> str:
        return self._url

    @property
    def is_success(self) -> bool:
        return False

    def __repr__(self) -> str:
        return f"<HttpxErrorResponse url={self.url!r} status={self.status_code} error={self._error!r}>"


class AsyncHttpx(IHTTPRequest):

    async def _get(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        r = await client.get(url)
        return r

    async def get(self, url: str) -> IResponse:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            return await self._get(client, url)

    async def get_many(self, urls: list[str], n: int):  # type: ignore[override]
        lists = sublist(urls, n)
        async with httpx.AsyncClient(follow_redirects=True) as client:
            for li in lists:
                tasks = [self._get(client, url) for url in li]
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                batch: list[IResponse] = []
                for url, r in zip(li, responses):
                    if isinstance(r, BaseException):
                        batch.append(HttpxErrorResponse(_url=url, _error=r))
                    else:
                        r.raw_url = url
                        batch.append(r)
                yield batch
