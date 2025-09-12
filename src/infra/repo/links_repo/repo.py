from datetime import date
from typing import Callable, cast

from sqlalchemy.ext.asyncio import AsyncSession

from ....app.repo.links_repo import ILinksRepo
from ....domain.entity.link import Link, LinksEntry, LinkStatus
from ...repo.links_repo.model import LinksDB, LinksEntryDB, LinkStatusDB


def links_orm_to_domain(links_db: LinksDB) -> Link:
    status_mapping = {
        LinkStatusDB.PENDING: LinkStatus.PENDING,
        LinkStatusDB.SUCCESS: LinkStatus.PROCESSED,
        LinkStatusDB.FAILED: LinkStatus.FAILED,
    }
    return Link(link=links_db.link, status=status_mapping[links_db.status])


def links_domain_to_orm(link: Link) -> LinksDB:
    status_mapping = {
        LinkStatus.PENDING: LinkStatusDB.PENDING,
        LinkStatus.PROCESSED: LinkStatusDB.SUCCESS,
        LinkStatus.FAILED: LinkStatusDB.FAILED,
    }
    return LinksDB(link=link.link, status=status_mapping[link.status])


def links_entry_orm_to_domain(links_entry: LinksEntryDB) -> LinksEntry:
    links: list[Link] = []
    for links_db in links_entry.links:
        status_mapping = {
            LinkStatusDB.PENDING: LinkStatus.PENDING,
            LinkStatusDB.SUCCESS: LinkStatus.PROCESSED,
            LinkStatusDB.FAILED: LinkStatus.FAILED,
        }

        link = Link(link=links_db.link, status=status_mapping[links_db.status])
        links.append(link)

    return LinksEntry(
        entity=links_entry.entity,
        group=links_entry.group,
        date=links_entry.date,
        links=links,
    )


# def links


class LinksRepo(ILinksRepo):

    def __init__(self, session_factory: Callable[[], AsyncSession]):
        self.session_factory = session_factory

    async def save_links(
        self, entity_name: str, group: str, date: date, links: list[Link]
    ) -> None:
        db_session = self.session_factory()

        try:
            links_entry: LinksEntryDB | None = cast(
                LinksEntryDB,
                await self._get_links_entry(
                    db_session=db_session,
                    entity_name=entity_name,
                    group=group,
                    date=date,
                    convert=False,
                    create=True,
                ),
            )

            for link in links:
                links_entry.links.append(links_domain_to_orm(link))
                db_session.add(links_entry)

            await db_session.commit()
        finally:
            await db_session.close()

    async def get_links(
        self, entity_name: str, group: str, date: date, create: bool = True
    ) -> list[Link]:

        db_session = self.session_factory()
        try:
            links_entry = await self._get_links_entry(
                db_session=db_session,
                entity_name=entity_name,
                group=group,
                date=date,
                convert=True,
                create=create,
            )

            if not links_entry:
                return []  # No links yet

            links: list[Link] = []
            for links_db in links_entry.links:
                link = Link(link=links_db.link, status=links_db.status)
                links.append(link)
            return links
        finally:
            await db_session.close()

    async def get_pending_range(
        self, entity_name: str, group: str, start: date, end: date
    ) -> list[LinksEntry]:

        db_session = self.session_factory()
        try:
            links_entry: list[LinksEntry] = cast(
                list[LinksEntry],
                await self._get_links_entry_range(
                    db_session=db_session,
                    entity_name=entity_name,
                    group=group,
                    start_date=start,
                    end_date=end,
                    convert=True,
                ),
            )
            for le in links_entry:
                le.links = [
                    link for link in le.links if link.status == LinkStatus.PENDING
                ]
            return links_entry
        finally:
            await db_session.close()

    async def mark_as_done(
        self, entity_name: str, group: str, date: date, links: list[str]
    ) -> None: ...

    async def _get_links_entry(
        self,
        db_session: AsyncSession,
        entity_name: str,
        group: str,
        date: date,
        convert: bool = True,
        create: bool = True,
    ) -> LinksEntry | LinksEntryDB | None:
        link_entry = await self._get_links_entry_range(
            db_session=db_session,
            entity_name=entity_name,
            group=group,
            start_date=date,
            end_date=date,
            convert=convert,
        )
        if not link_entry and create:
            new_le = LinksEntryDB(entity=entity_name, group=group, date=date)
            db_session.add(new_le)
            link_entry = [new_le]
            await db_session.flush()  # Get the ID

        if not link_entry:
            return None
        return link_entry[0]

    async def _get_links_entry_range(
        self,
        db_session: AsyncSession,
        entity_name: str,
        group: str,
        start_date: date,
        end_date: date,
        convert: bool = True,
    ) -> list[LinksEntry | LinksEntryDB]:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        # Get linksEntry according to entity_name, group and date range
        stmt = (
            select(LinksEntryDB)
            .where(
                LinksEntryDB.entity == entity_name,
                LinksEntryDB.group == group,
                LinksEntryDB.date >= start_date,
                LinksEntryDB.date <= end_date,
            )
            .options(selectinload(LinksEntryDB.links))
        )
        result = await db_session.execute(stmt)
        links_entries = result.scalars().all()

        if convert:
            return [links_entry_orm_to_domain(entry) for entry in links_entries]
        else:
            return list(links_entries)
