from dataclasses import dataclass
from datetime import date
from logging import Logger
from typing import Dict, List, Optional

from src.app.repo.links_repo import ILinksRepo
from src.app.usecase.usecase import UseCase
from src.domain.entity.Link import Link, LinkStatus


@dataclass
class LinkReader(UseCase):

    links_repo: ILinksRepo
    logger: Logger

    async def execute(
        self,
        entity_name: str,
        group: str,
        target_date: date,
        status_filter: Optional[str] = None,
    ) -> List[Link]:

        status_filter_enum = LinkStatus(status_filter) if status_filter else None
        try:
            links = await self.links_repo.get_links(entity_name, group, target_date)

            if status_filter_enum:
                # Filter by status if specified
                filtered_links = [
                    link for link in links if link.status == status_filter_enum
                ]
                self.logger.info(
                    f"Retrieved {len(filtered_links)} {status_filter_enum.value} links for {entity_name}:{group} on {target_date}"
                )
                return filtered_links

            self.logger.info(
                f"Retrieved {len(links)} links for {entity_name}:{group} on {target_date}"
            )
            return links

        except Exception as e:
            self.logger.error(
                f"Error reading links for {entity_name}:{group} on {target_date}: {e}"
            )
            raise


@dataclass
class LinkReaderRange(UseCase):

    link_reader: LinkReader
    logger: Logger

    async def execute(
        self,
        entity_name: str,
        group: str,
        start: date,
        end: date,
        status_filter: Optional[str] = None,
    ) -> Dict[date, List[Link]]:

        from src.domain.service.weekdays import get_weekdays_from_range

        weekdays = get_weekdays_from_range(start=start, end=end)

        results: Dict[date, List[Link]] = {}

        self.logger.info(
            f"Starting range reading for {entity_name}:{group} from {start} to {end} ({len(weekdays)} weekdays)"
        )

        # Use composed LinkReader for each weekday in the range
        for weekday in weekdays:
            status_filter_enum = LinkStatus(status_filter) if status_filter else None
            try:
                links = await self.link_reader.execute(
                    entity_name, group, weekday, status_filter_enum
                )
                results[weekday] = links

                if links:
                    self.logger.debug(
                        f"Read {len(links)} links for {entity_name}:{group} on {weekday}"
                    )
            except Exception as e:
                # Handle exceptions but continue processing other days
                self.logger.error(
                    f"Failed to read links for {entity_name}:{group} on {weekday}: {e}"
                )
                results[weekday] = []  # Empty list for failed days

        total_links = sum(len(links) for links in results.values())
        self.logger.info(
            f"Range reading completed for {entity_name}:{group}: {total_links} total links across {len(weekdays)} weekdays"
        )

        return results
