from dataclasses import dataclass
from datetime import date
from logging import Logger
from typing import Dict, Optional

from .getlinks import LinkCollector
from .readlinks import LinkReader

from ..gateway.links import IGetLink
from ..repo.links_repo import ILinksRepo
from ..usecase.usecase import UseCase
from ...domain.entity.link import Link, merge_links
from ...domain.service.weekdays import get_weekdays_from_range


@dataclass
class LinkRetry(UseCase):

    collect: LinkCollector
    read: LinkReader

    async def execute(
        self,
        entity_name: str,
        group: str,
        start: date,
        end: Optional[date],
        commit: Optional[bool],
        status_filter: Optional[str],
    ) -> Dict[date, list[Link]]:
        
        links = await self.read.execute(
            entity_name=entity_name,
            group=group,
            start=start,
            end=end,
            commit=None,
            status_filter=None
        )
        empty_days = [day for day, links in links.items() if not links]
        results = {}
        for day in empty_days:
            links = await self.collect.execute(
                entity_name=entity_name,
                group=group,
                start=start,
                end=None,
                commit=None,
                status_filter=None
            )
            if links:
                results[day] = links[day]
        return results