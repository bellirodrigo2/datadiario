from datetime import date

from dou.app.repo.links_repo import ILinksRepo
from dou.domain.entity.Link import Link, LinkStatus
from dou.infra.repo.links_repo.model import LinksDB, LinksEntryDB, LinkStatusDB
from sqlalchemy.ext.asyncio import AsyncSession


class LinksRepo(ILinksRepo):

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

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

        result = await self.db_session.execute(stmt)
        links_entry = result.scalar_one_or_none()

        if not links_entry:
            links_entry = LinksEntryDB(entity=entity_name, group=group, date=date)
            self.db_session.add(links_entry)
            await self.db_session.flush()  # Get the ID

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
            self.db_session.add(links_db)

        await self.db_session.commit()

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

        result = await self.db_session.execute(stmt)
        links_entry = result.scalar_one_or_none()

        # If does not exist, create one and commit
        if not links_entry:
            links_entry = LinksEntryDB(entity=entity_name, group=group, date=date)
            self.db_session.add(links_entry)
            await self.db_session.commit()
            return []  # No links yet

        # Return links converting LinksDB to Links
        links = []
        for links_db in links_entry.links:
            status_mapping = {
                LinkStatusDB.PENDING: LinkStatus.PENDING,
                LinkStatusDB.SUCCESS: LinkStatus.PROCESSED,
                LinkStatusDB.FAILED: LinkStatus.FAILED,
            }

            link = Link(link=links_db.link, status=status_mapping[links_db.status])
            links.append(link)

        return links
