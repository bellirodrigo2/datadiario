from datetime import date
from typing import Protocol

from ...domain.entity.link import Link, LinksEntry


class ILinksRepo(Protocol):
    async def save_links(
        self, entity_name: str, group: str, date: date, links: list[Link]
    ) -> None: ...

    async def get_links(
        self, entity_name: str, group: str, date: date
    ) -> list[Link]: ...

    async def get_pending_range(
        self, entity_name: str, group: str, start: date, end: date
    ) -> list[LinksEntry]: ...

    async def mark_as_done(
        self, entity_name: str, group: str, date: date, links: list[str]
    ) -> None: ...
