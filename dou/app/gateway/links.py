from datetime import datetime
from typing import Protocol


class IGetLink(Protocol):
    async def __call__(self, date: datetime) -> list[str]: ...


class IGetLinkRegistry(Protocol):
    def get(self, entity_name: str, group: str) -> IGetLink: ...
    def add(self, entity_name: str, group: str, get_link: IGetLink) -> None: ...
