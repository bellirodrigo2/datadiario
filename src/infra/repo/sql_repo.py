from datetime import date

from ...app.repo.links_repo import ILinksRepo
from ...domain.entity.link import Link, LinksEntry, LinkStatus
from ..db.connection import DatabaseConnection


def links_orm_to_domain(link_data: dict) -> Link:
    status_mapping = {
        "pending": LinkStatus.PENDING,
        "success": LinkStatus.PROCESSED,
        "failed": LinkStatus.FAILED,
    }
    return Link(link=link_data["link"], status=status_mapping[link_data["status"]])


def links_domain_to_orm(link: Link) -> dict:
    status_mapping = {
        LinkStatus.PENDING: "pending",
        LinkStatus.PROCESSED: "success",
        LinkStatus.FAILED: "failed",
    }
    return {"link": link.link, "status": status_mapping[link.status]}


class SQLLinksRepo(ILinksRepo):

    def __init__(self, db_adapter: DatabaseConnection):
        self.db_adapter = db_adapter

    def save_links(
        self, entity_name: str, group: str, date: date, links: list[Link]
    ) -> None:
        try:
            # First, ensure the links_entry exists
            links_entry_id = self._ensure_links_entry(entity_name, group, date)

            # Insert all new links
            for link in links:
                link_data = links_domain_to_orm(link)
                insert_sql = """
                    INSERT INTO links (links_entry_id, link, status)
                    VALUES (?, ?, ?)
                """
                self.db_adapter.execute(
                    insert_sql, (links_entry_id, link_data["link"], link_data["status"])
                )

            self.db_adapter.commit()
        except Exception:
            self.db_adapter.rollback()
            raise

    def get_links(
        self, entity_name: str, group: str, date: date, create: bool = True
    ) -> list[Link]:

        # Get links_entry_id
        links_entry_id = self._get_links_entry_id(entity_name, group, date, create)

        if not links_entry_id:
            return []

        # Get all links for this entry
        select_sql = """
            SELECT link, status
            FROM links
            WHERE links_entry_id = ?
        """
        rows = self.db_adapter.query(select_sql, (links_entry_id,))

        links = []
        for row in rows:
            link_data = {"link": row[0], "status": row[1]}
            link = links_orm_to_domain(link_data)
            links.append(link)

        return links

    def get_pending_range(
        self, entity_name: str, group: str, start: date, end: date
    ) -> list[LinksEntry]:

        # Get all links_entries in date range with pending links
        select_sql = """
            SELECT DISTINCT le.id, le.entity, le.group_name, le.date
            FROM links_entry le
            JOIN links l ON l.links_entry_id = le.id
            WHERE le.entity = ?
              AND le.group_name = ?
              AND le.date >= ?
              AND le.date <= ?
              AND l.status = 'pending'
            ORDER BY le.date
        """
        entries_rows = self.db_adapter.query(
            select_sql, (entity_name, group, start, end)
        )

        links_entries = []
        for entry_row in entries_rows:
            entry_id, entity, group_name, entry_date = entry_row

            # Get pending links for this entry
            links_sql = """
                SELECT link, status
                FROM links
                WHERE links_entry_id = ? AND status = 'pending'
            """
            links_rows = self.db_adapter.query(links_sql, (entry_id,))

            links = []
            for link_row in links_rows:
                link_data = {"link": link_row[0], "status": link_row[1]}
                link = links_orm_to_domain(link_data)
                links.append(link)

            links_entry = LinksEntry(
                entity=entity, group=group_name, date=entry_date, links=links
            )
            links_entries.append(links_entry)

        return links_entries

    def mark_as_done(
        self, entity_name: str, group: str, date: date, links: list[str]
    ) -> None:
        try:
            if not links:
                return  # Nothing to mark

            # Direct UPDATE with JOIN - simpler and more direct
            placeholders = ",".join(["?" for _ in links])
            update_sql = f"""
                UPDATE links
                SET status = 'success'
                WHERE links_entry_id IN (
                    SELECT id FROM links_entry
                    WHERE entity = ? AND group_name = ? AND date = ?
                )
                AND link IN ({placeholders})
            """

            params = [entity_name, group, date] + links
            self.db_adapter.execute(update_sql, tuple(params))
            self.db_adapter.commit()
        except Exception:
            self.db_adapter.rollback()
            raise

    def _ensure_links_entry(self, entity_name: str, group: str, date: date) -> int:
        """Ensure links_entry exists and return its ID"""

        # Try to get existing entry
        select_sql = """
            SELECT id FROM links_entry
            WHERE entity = ? AND group_name = ? AND date = ?
        """
        rows = self.db_adapter.query(select_sql, (entity_name, group, date))

        if rows:
            return rows[0][0]

        # Create new entry
        insert_sql = """
            INSERT INTO links_entry (entity, group_name, date)
            VALUES (?, ?, ?)
        """
        return self.db_adapter.execute(insert_sql, (entity_name, group, date))

    def _get_links_entry_id(
        self, entity_name: str, group: str, date: date, create: bool = True
    ) -> int | None:
        """Get links_entry ID, optionally creating if not exists"""

        select_sql = """
            SELECT id FROM links_entry
            WHERE entity = ? AND group_name = ? AND date = ?
        """
        rows = self.db_adapter.query(select_sql, (entity_name, group, date))

        if rows:
            return rows[0][0]

        if create:
            return self._ensure_links_entry(entity_name, group, date)

        return None
