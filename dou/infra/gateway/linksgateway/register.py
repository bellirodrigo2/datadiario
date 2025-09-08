import asyncio
from datetime import datetime

from dou.app.gateway.links import IGetLink, IGetLinkRegistry
from dou.infra.gateway.linksgateway.br import (
    get_br_dou1_links,
    get_br_dou2_links,
    get_br_dou3_links,
)


class AsyncWrapper:
    """Wrapper to make synchronous link collectors async"""

    def __init__(self, sync_func):
        self.sync_func = sync_func

    async def __call__(self, date: datetime) -> list[str]:
        # Run the synchronous function in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.sync_func, date)


class GetLinkRegistry(IGetLinkRegistry):

    def __init__(self):
        self._registry: dict[tuple[str, str], IGetLink] = {}

    def get(self, entity_name: str, group: str) -> IGetLink:
        return self._registry[(entity_name, group)]

    def add(self, entity_name: str, group: str, get_link: IGetLink) -> None:
        self._registry[(entity_name, group)] = get_link


get_link_registry = GetLinkRegistry()


# GOVERNO FEDERAL - Wrapped with AsyncWrapper to make them async
get_link_registry.add("br_federal", "dou1", AsyncWrapper(get_br_dou1_links))
get_link_registry.add("br_federal", "dou2", AsyncWrapper(get_br_dou2_links))
get_link_registry.add("br_federal", "dou3", AsyncWrapper(get_br_dou3_links))
