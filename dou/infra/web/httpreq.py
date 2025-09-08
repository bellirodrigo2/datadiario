import asyncio
from dataclasses import dataclass
from typing import Any, Iterable, Protocol

import aiohttp
import requests


class ResponseInterface(Protocol):
    @property
    def status_code(self) -> int: ...
    @property
    def response(self) -> str: ...
    @property
    def content(self) -> bytes: ...
    @property
    def url(self) -> str: ...


@dataclass
class AiohttpResponse(ResponseInterface):
    _response: aiohttp.ClientResponse

    @property
    def status_code(self) -> int:
        return self._response.status

    @property
    async def response(self) -> str:  # type: ignore
        return await self._response.text()  # type: ignore

    @property
    async def content(self) -> bytes:  # type: ignore
        return await self._response.read()  # type: ignore

    @property
    def url(self) -> str:
        return str(self._response.url)


@dataclass
class RequestsResponse(ResponseInterface):
    _response: requests.Response

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def response(self) -> str:
        return self._response.text

    @property
    def content(self) -> bytes:
        return self._response.content

    @property
    def url(self) -> str:
        return str(self._response.url)


class HTTPRequest(Protocol):

    def get(self, url) -> ResponseInterface: ...

    def get_many(self, urls: list[str], n: int) -> Iterable[ResponseInterface]: ...


def sublist(lista: list[Any], n: int):
    return [lista[i : i + n] for i in range(0, len(lista), n)]


class AsyncRequest(HTTPRequest):

    async def _get(self, session: aiohttp.ClientSession, url):
        async with session.get(url) as response:
            return response

    async def get(self, url):
        async with aiohttp.ClientSession() as session:
            return self._get(session, url)

    async def get_many(self, urls: list[str], n: int):

        lists = sublist(urls, n)
        async with aiohttp.ClientSession() as session:
            for li in lists:
                try:
                    tarefas = [self._get(session, url) for url in li]
                    yield await asyncio.gather(*tarefas)
                except Exception as e:
                    yield li


class SyncRequest(HTTPRequest):

    def _get(self, session: requests.Session, url: str):
        response = session.get(url)
        return response

    def get(self, url: str):
        with requests.Session() as session:
            return self._get(session, url)

    def get_many(self, urls: list[str], n: int):
        lists = sublist(urls, n)
        with requests.Session() as session:
            for li in lists:
                try:
                    yield [self._get(session, url) for url in li]
                except Exception as e:
                    yield li


if __name__ == "__main__":
    ...

    # async def batch_request(urls: list[str], n: int):
#     async def async_batch_request(urls: list[str], n: int):

#         def sublist(lista: list[Any], n: int):
#             return [lista[i : i + n] for i in range(0, len(lista), n)]

#         async def httprequest(session: aiohttp.ClientSession, url: str):
#             async with session.get(url) as response:
#                 return response

#         lists = sublist(urls, n)

#         req_ok: list[aiohttp.ClientResponse] = []
#         req_error: list[aiohttp.ClientResponse] = []
#         fails: list[tuple[Exception, list[str]]] = []
#         async with aiohttp.ClientSession() as session:
#             for li in lists:
#                 try:
#                     tarefas = [httprequest(session, url) for url in li]

#                     resultados = await asyncio.gather(*tarefas)

#                     oks = [resp for resp in resultados if resp.status == 200]
#                     errors = [resp for resp in resultados if resp.status != 200]

#                     req_ok.extend(oks)
#                     req_error.extend(errors)
#                 except Exception as e:
#                     fails.append((e, li))
#         return req_ok, req_error, fails

#     return await async_batch_request(urls, n)
