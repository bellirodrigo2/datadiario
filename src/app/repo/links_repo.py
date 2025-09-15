from datetime import date
from typing import Protocol

from ...domain.entity.link import Link, LinksEntry


class ILinksRepo(Protocol):
    def save_links(
        self, entity_name: str, group: str, date: date, links: list[Link]
    ) -> None: ...

    def get_links(self, entity_name: str, group: str, date: date) -> list[Link]: ...

    def get_pending_range(
        self, entity_name: str, group: str, start: date, end: date
    ) -> list[LinksEntry]: ...

    def mark_as_done(
        self, entity_name: str, group: str, date: date, links: list[str]
    ) -> None: ...
