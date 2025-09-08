from datetime import date

import pytest
import pytest_asyncio
from dou.domain.entity.Link import Link, LinkStatus
from dou.infra.repo.links_repo.db import make_session
from dou.infra.repo.links_repo.model import Base
from dou.infra.repo.links_repo.repo import LinksRepo
from sqlalchemy.ext.asyncio import AsyncSession


class TestLinksRepo:

    @pytest_asyncio.fixture
    async def db_session(self):
        # Use in-memory SQLite for testing
        session_factory = await make_session("sqlite+aiosqlite:///:memory:", Base)
        async with session_factory() as session:
            yield session

    @pytest.mark.asyncio
    async def test_save_links_creates_entry_with_multiple_links(self, db_session):
        # Arrange
        links_repo = LinksRepo(db_session)
        entity_name = "BR"
        group = "DOU1"
        test_date = date(2023, 1, 15)
        links = [
            Link(link="https://example.com/1"),
            Link(link="https://example.com/2"),
            Link(link="https://example.com/3"),
        ]

        # Act
        await links_repo.save_links(entity_name, group, test_date, links)

        # Assert - Use repository method to verify data was saved
        retrieved_links = await links_repo.get_links(entity_name, group, test_date)

        assert len(retrieved_links) == 3
        retrieved_urls = [link.link for link in retrieved_links]
        retrieved_statuses = [link.status for link in retrieved_links]

        for expected_link in links:
            assert expected_link.link in retrieved_urls
        assert all(status == LinkStatus.PENDING for status in retrieved_statuses)

    @pytest.mark.asyncio
    async def test_save_links_with_empty_list(self, db_session):
        # Arrange
        links_repo = LinksRepo(db_session)
        entity_name = "BR"
        group = "DOU2"
        test_date = date(2023, 2, 20)
        links = []

        # Act
        await links_repo.save_links(entity_name, group, test_date, links)

        # Assert - Use repository method to verify empty entry was created
        retrieved_links = await links_repo.get_links(entity_name, group, test_date)
        assert retrieved_links == []

    @pytest.mark.asyncio
    async def test_save_links_with_single_link(self, db_session):
        # Arrange
        links_repo = LinksRepo(db_session)
        entity_name = "US"
        group = "GOV"
        test_date = date(2023, 3, 10)
        links = [Link(link="https://single-link.com")]

        # Act
        await links_repo.save_links(entity_name, group, test_date, links)

        # Assert - Use repository method to verify single link was saved
        retrieved_links = await links_repo.get_links(entity_name, group, test_date)

        assert len(retrieved_links) == 1
        assert retrieved_links[0].link == "https://single-link.com"
        assert retrieved_links[0].status == LinkStatus.PENDING

    @pytest.mark.asyncio
    async def test_save_links_persists_data_correctly(self, db_session):
        # Arrange
        links_repo = LinksRepo(db_session)
        entity_name = "BR"
        group = "DOU1"
        test_date = date(2023, 1, 15)
        links = [Link(link="https://link1.com"), Link(link="https://link2.com")]

        # Act
        await links_repo.save_links(entity_name, group, test_date, links)

        # Assert - Use repository method to verify persistence
        retrieved_links = await links_repo.get_links(entity_name, group, test_date)

        assert len(retrieved_links) == 2
        retrieved_urls = [link.link for link in retrieved_links]
        retrieved_statuses = [link.status for link in retrieved_links]

        assert "https://link1.com" in retrieved_urls
        assert "https://link2.com" in retrieved_urls
        assert all(status == LinkStatus.PENDING for status in retrieved_statuses)

    @pytest.mark.asyncio
    async def test_get_links_returns_saved_links(self, db_session):
        # Arrange
        links_repo = LinksRepo(db_session)
        entity_name = "BR"
        group = "DOU1"
        test_date = date(2023, 1, 15)
        links = [Link(link="https://link1.com"), Link(link="https://link2.com")]

        # Save links first
        await links_repo.save_links(entity_name, group, test_date, links)

        # Act
        retrieved_links = await links_repo.get_links(entity_name, group, test_date)

        # Assert
        assert len(retrieved_links) == 2
        link_urls = [link.link for link in retrieved_links]
        link_statuses = [link.status for link in retrieved_links]

        assert "https://link1.com" in link_urls
        assert "https://link2.com" in link_urls
        assert all(status == LinkStatus.PENDING for status in link_statuses)

    @pytest.mark.asyncio
    async def test_get_links_returns_empty_for_nonexistent_entry(self, db_session):
        # Arrange
        links_repo = LinksRepo(db_session)
        entity_name = "BR"
        group = "DOU1"
        test_date = date(2023, 1, 15)

        # Act - Try to get links without saving any
        retrieved_links = await links_repo.get_links(entity_name, group, test_date)

        # Assert
        assert retrieved_links == []

    @pytest.mark.asyncio
    async def test_get_links_filters_by_entity_group_date(self, db_session):
        # Arrange
        links_repo = LinksRepo(db_session)

        # Save links for different entities/groups/dates
        await links_repo.save_links(
            "BR", "DOU1", date(2023, 1, 15), [Link(link="https://br-dou1.com")]
        )
        await links_repo.save_links(
            "BR", "DOU2", date(2023, 1, 15), [Link(link="https://br-dou2.com")]
        )
        await links_repo.save_links(
            "US", "DOU1", date(2023, 1, 15), [Link(link="https://us-dou1.com")]
        )
        await links_repo.save_links(
            "BR", "DOU1", date(2023, 1, 16), [Link(link="https://br-dou1-16.com")]
        )

        # Act - Get specific entry
        retrieved_links = await links_repo.get_links(
            "BR", "DOU1", date(2023, 1, 15)
        )

        # Assert
        assert len(retrieved_links) == 1
        assert retrieved_links[0].link == "https://br-dou1.com"
        assert retrieved_links[0].status == LinkStatus.PENDING

    @pytest.mark.asyncio
    async def test_status_conversion_domain_to_db_and_back(self, db_session):
        # Arrange
        links_repo = LinksRepo(db_session)
        entity_name = "BR"
        group = "DOU1"
        test_date = date(2023, 1, 15)
        links = [Link(link="https://test-link.com")]

        # Act - Save links (uses domain PENDING status internally converted to DB)
        await links_repo.save_links(entity_name, group, test_date, links)

        # Get links back (should convert DB status back to domain)
        retrieved_links = await links_repo.get_links(entity_name, group, test_date)

        # Assert - Status should be domain LinkStatus.PENDING
        assert len(retrieved_links) == 1
        assert retrieved_links[0].link == "https://test-link.com"
        assert retrieved_links[0].status == LinkStatus.PENDING
        assert isinstance(retrieved_links[0].status, LinkStatus)

    def test_links_repo_initialization(self):
        # Arrange
        from unittest.mock import Mock

        mock_session = Mock()

        # Act
        repo = LinksRepo(mock_session)

        # Assert
        assert repo.db_session == mock_session