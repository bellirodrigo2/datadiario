from dataclasses import dataclass
from datetime import date
from logging import Logger
from typing import Dict

from dou.app.gateway.links import IGetLinkRegistry
from dou.app.repo.links_repo import ILinksRepo
from dou.app.usecase.usecase import UseCase
from dou.domain.entity.Link import Link, LinkStatus
from dou.domain.service.weekdays import get_weekdays, get_weekdays_from_range


def process_links(new_links: list[str], existing_links: list[str]) -> list[str]:

    existing_links_set = {
        link.link for link in existing_links if link.status == LinkStatus.FAILED
    }
    return [link for link in new_links if link not in existing_links_set]


@dataclass
class LinkCollector(UseCase):

    registry: IGetLinkRegistry
    links_repo: ILinksRepo
    logger: Logger

    async def execute(
        self, entity_name: str, group: str, date: date, commit: bool
    ) -> list[str]:

        try:
            get_link = self.registry.get(
                entity_name, group
            )  # raises KeyError if not found
            links_str = await get_link(date)
            self.logger.info(
                f"Collected {len(links_str)} links for {entity_name}:{group} on {date}"
            )
            if not commit:
                return links_str
        except KeyError:
            self.logger.error(f"No link collector registered for {entity_name}:{group}")
            raise ValueError(f"No link collector registered for {entity_name}:{group}")

        links = [Link(link=link_str) for link_str in links_str]

        existing_links = await self.links_repo.get_links(entity_name, group, date)

        # Create a set of existing link URLs for fast lookup
        existing_urls = {elink.link for elink in existing_links}
        existing_failed_urls = {
            elink.link for elink in existing_links if elink.status == LinkStatus.FAILED
        }

        new_links: list[Link] = []

        # Add new links that don't exist yet, or retry failed ones
        for link in links:
            if link.link not in existing_urls or link.link in existing_failed_urls:
                new_links.append(link)

        # Save all new/retry links at once
        if new_links:
            await self.links_repo.save_links(entity_name, group, date, new_links)

        self.logger.info(
            f"Saved {len(new_links)} new links for {entity_name}:{group} on {date}"
        )
        return [link.link for link in new_links]


@dataclass
class LinkCollectorRange(UseCase):

    link_collector: LinkCollector
    logger: Logger

    async def execute(
        self, entity_name: str, group: str, start: date, end: date, commit: bool
    ) -> Dict[date, list[str]]:
        weekdays = get_weekdays_from_range(start=start, end=end)
        
        results: Dict[date, list[str]] = {}
        
        self.logger.info(
            f"Starting range collection for {entity_name}:{group} from {start} to {end} ({len(weekdays)} weekdays)"
        )
        
        # Use composed LinkCollector for each weekday in the range
        for weekday in weekdays:
            try:
                links = await self.link_collector.execute(entity_name, group, weekday, commit)
                results[weekday] = links
                
                if links:
                    self.logger.debug(
                        f"Collected {len(links)} links for {entity_name}:{group} on {weekday}"
                    )
            except ValueError as e:
                # Re-raise ValueError (e.g., missing collector) - this should stop execution
                self.logger.error(f"No link collector registered for {entity_name}:{group}")
                raise e
            except Exception as e:
                # Handle other exceptions but continue processing other days
                self.logger.error(
                    f"Failed to collect links for {entity_name}:{group} on {weekday}: {e}"
                )
                results[weekday] = []  # Empty list for failed days
        
        total_links = sum(len(links) for links in results.values())
        self.logger.info(
            f"Range collection completed for {entity_name}:{group}: {total_links} total links across {len(weekdays)} weekdays"
        )
        
        return results
