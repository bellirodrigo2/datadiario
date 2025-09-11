from datetime import date
from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession
from ....app.repo.links_repo import ILinksRepo
from ....domain.entity.link import Link, LinkStatus
from ...repo.links_repo.model import LinksDB, LinksEntryDB, LinkStatusDB


class LinksRepo(ILinksRepo):

    def __init__(self, session_factory: Callable[[], AsyncSession]):
        self.session_factory = session_factory

    async def save_links(
        self, entity_name: str, group: str, date: date, links: list[Link]
    ) -> None:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # First, find or create the LinksEntry
        stmt = (
            select(LinksEntryDB)
            .where(
                LinksEntryDB.entity == entity_name,
                LinksEntryDB.group == group,
                LinksEntryDB.date == date,
            )
            .options(selectinload(LinksEntryDB.links))
        )
        db_session = self.session_factory()
        try:
            result = await db_session.execute(stmt)
            links_entry = result.scalar_one_or_none()

            if not links_entry:
                links_entry = LinksEntryDB(entity=entity_name, group=group, date=date)
                db_session.add(links_entry)
                await db_session.flush()  # Get the ID

            # Convert Link domain entities to LinksDB models
            for link in links:
                status_mapping = {
                    LinkStatus.PENDING: LinkStatusDB.PENDING,
                    LinkStatus.PROCESSED: LinkStatusDB.SUCCESS,
                    LinkStatus.FAILED: LinkStatusDB.FAILED,
                }

                links_db = LinksDB(
                    id_entry=links_entry.id,
                    link=link.link,
                    status=status_mapping[link.status],
                    msg=None,
                )
                db_session.add(links_db)

            await db_session.commit()
        finally:
            await db_session.close()

    async def get_links(self, entity_name: str, group: str, date: date) -> list[Link]:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # Get linksEntry according to entity_name, group and date
        stmt = (
            select(LinksEntryDB)
            .where(
                LinksEntryDB.entity == entity_name,
                LinksEntryDB.group == group,
                LinksEntryDB.date == date,
            )
            .options(selectinload(LinksEntryDB.links))
        )
        db_session = self.session_factory()
        try:
            result = await db_session.execute(stmt)
            links_entry = result.scalar_one_or_none()

            if not links_entry:
                links_entry = LinksEntryDB(entity=entity_name, group=group, date=date)
                db_session.add(links_entry)
                await db_session.commit()
                return []  # No links yet

            links: list[Link] = []
            for links_db in links_entry.links:
                status_mapping = {
                    LinkStatusDB.PENDING: LinkStatus.PENDING,
                    LinkStatusDB.SUCCESS: LinkStatus.PROCESSED,
                    LinkStatusDB.FAILED: LinkStatus.FAILED,
                }

                link = Link(link=links_db.link, status=status_mapping[links_db.status])
                links.append(link)

            return links
        finally:
            await db_session.close()
