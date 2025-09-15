from dataclasses import dataclass
from datetime import date
from logging import Logger
from typing import Dict, List, Optional

from rich.console import Console

from ...domain.entity.link import Link, LinkStatus
from ..repo.links_repo import ILinksRepo
from .usecase import UseCase

console = Console()


@dataclass
class LinkReader(UseCase):

    links_repo: ILinksRepo
    logger: Logger

    async def execute(
        self,
        entity_name: str,
        group: str,
        start: date,
        end: Optional[date],
        commit: Optional[bool],
        status_filter: Optional[str],
    ) -> Dict[date, List[Link]]:

        weekdays = self._get_weekdays(start=start, end=end)

        results: Dict[date, List[Link]] = {}

        status_filter_enum = LinkStatus(status_filter) if status_filter else None

        for weekday in weekdays:
            try:
                links = await self.read_single_day(
                    entity_name, group, weekday, status_filter_enum
                )
                results[weekday] = links

                if links:
                    self.logger.debug(
                        f"Read {len(links)} links for {entity_name}:{group} on {weekday}"
                    )
            except Exception as e:
                self.logger.error(
                    f"Failed to read links for {entity_name}:{group} on {weekday}: {e}"
                )
                results[weekday] = []  # Empty list for failed days

        return results

    async def read_single_day(
        self,
        entity_name: str,
        group: str,
        target_date: date,
        status_filter: Optional[LinkStatus] = None,
    ) -> List[Link]:
        try:
            links = self.links_repo.get_links(entity_name, group, target_date)
            status_filter_enum = LinkStatus(status_filter) if status_filter else None
            if status_filter_enum:
                # Filter by status if specified
                filtered_links = [
                    link for link in links if link.status == status_filter_enum
                ]
                return filtered_links
            return links

        except Exception as e:
            self.logger.error(
                f"Error reading links for {entity_name}:{group} on {target_date}: {e}"
            )
            raise
