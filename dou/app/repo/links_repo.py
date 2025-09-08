from datetime import date
from typing import Protocol

from dou.domain.entity.Link import Link


class ILinksRepo(Protocol):
    async def save_links(
        self, entity_name: str, group: str, date: date, links: list[Link]
    ) -> None: ...

    async def get_links(
        self, entity_name: str, group: str, date: date
    ) -> list[Link]: ...
