from dataclasses import dataclass
from datetime import date
from logging import Logger
from typing import Dict, List, Mapping, Optional
from rich.console import Console


from ..gateway.links import IGetLink
from ..repo.links_repo import ILinksRepo
from ..usecase.usecase import UseCase
from ...domain.entity.link import Link, LinkStatus, merge_links
from ...domain.service.weekdays import get_weekdays_from_range

console = Console()

@dataclass
class LinkCollector(UseCase):

    registry: Mapping[str, IGetLink]
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
    ) -> Dict[date, list[Link]]:

        if end is None:
            end = start

        weekdays = get_weekdays_from_range(start, end)
        
        if not weekdays:
            self.logger.warning(f"No weekdays found in the range {start} to {end}.")
            return []

        results: Dict[date, list[Link]] = {}

        # Use composed LinkCollector for each weekday in the range
        for weekday in weekdays:
            try:
                links = await self._collect_single_day(
                    entity_name, group, weekday, commit
                )
                results[weekday] = links
                console.print(f"Collected {len(links)} links for {entity_name}:{group} on {weekday}")
                if links:
                    self.logger.debug(
                        f"Collected {len(links)} links for {entity_name}:{group} on {weekday}"
                    )
            except ValueError as e:
                # Re-raise ValueError (e.g., missing collector) - this should stop execution
                self.logger.error(
                    f"No link collector registered for {entity_name}:{group}"
                )
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

    async def _collect_single_day(
        self,
        entity_name: str,
        group: str,
        target_date: date,
        commit: Optional[bool] = None,
    ) -> List[Link]:
        try:
            registry_key = f"{entity_name.upper()}:{group.upper()}"
            
            get_link = self.registry[registry_key]
            
            links_str = await get_link(target_date)
            
            self.logger.debug(f"Converting {len(links_str)} string links to Link objects")
            links = []
            for i, link_str in enumerate(links_str):
                try:
                    link_obj = Link(link=link_str)
                    links.append(link_obj)
                    if i < 3:  # Log only first few for debugging
                        self.logger.debug(f"Created Link object: {link_obj}")
                except Exception as e:
                    self.logger.error(f"Failed to create Link from '{link_str}': {e}")
                    raise
            
            if not commit:
                return links
        except KeyError:
            self.logger.error(f"No link collector registered for {entity_name}:{group}")
            raise ValueError(f"No link collector registered for {entity_name}:{group}")

        existing_links = await self.links_repo.get_links(
            entity_name, group, target_date
        )

        existing_urls = {elink.link for elink in existing_links}
        existing_failed_urls = {
            elink.link for elink in existing_links if elink.status == LinkStatus.FAILED
        }

        new_links: list[Link] = []

        for link in links:
            if link.link not in existing_urls or link.link in existing_failed_urls:
                new_links.append(link)

        if new_links:
            await self.links_repo.save_links(entity_name, group, target_date, new_links)

        return new_links
