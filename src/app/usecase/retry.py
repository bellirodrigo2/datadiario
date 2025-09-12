from dataclasses import dataclass
from datetime import date
from logging import Logger
from typing import Dict, Optional

from .getlinks import LinkCollector
from .readlinks import LinkReader

from ..usecase.usecase import UseCase
from ...domain.entity.link import Link
from ...domain.service.weekdays import  is_weekday


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
        empty_days = [day for day, links in links.items() if len(links)==0]
        results = {}
        weekday_empty = [day for day in empty_days if is_weekday(day)]
        for day in weekday_empty:
            links = await self.collect.collect_single_day(
                entity_name=entity_name,
                group=group,
                target_date=day,
                commit=commit,
            )
            if links:
                results[day] = links[day]
        return results