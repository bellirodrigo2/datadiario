import logging
from datetime import date
from unittest.mock import Mock

import pytest
import pytest_asyncio
from dou.app.usecase.readlinks import LinkReader
from dou.domain.entity.Link import Link, LinkStatus
from dou.infra.repo.links_repo.db import make_session
from dou.infra.repo.links_repo.model import Base
from dou.infra.repo.links_repo.repo import LinksRepo


class TestLinkReader:

    @pytest_asyncio.fixture
    async def db_session(self):
        """Create in-memory database session for testing"""
        session_factory = await make_session("sqlite+aiosqlite:///:memory:", Base)
        async with session_factory() as session:
            yield session

    @pytest.fixture
    def mock_logger(self):
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def link_reader(self, db_session, mock_logger):
        """Create LinkReader using DI container with test dependencies"""
        from dependency_injector import providers
        from dou.infra.di import Container

        container = Container()
        container.provide("logger", providers.Object(mock_logger))
        container.provide("links_repo", providers.Object(LinksRepo(db_session)))
        container.provide(
            "link_reader",
            providers.Factory(
                LinkReader,
                links_repo=container._container.links_repo,
                logger=container._container.logger,
            ),
        )

        return container.inject("link_reader")

    async def _populate_test_links(
        self, link_reader, entity_name: str, group: str, test_date: date
    ):
        """Helper method to populate test data"""
        test_links = [
            Link(link="https://pending1.com", status=LinkStatus.PENDING),
            Link(link="https://pending2.com", status=LinkStatus.PENDING),
            Link(link="https://processed1.com", status=LinkStatus.PROCESSED),
            Link(link="https://processed2.com", status=LinkStatus.PROCESSED),
            Link(link="https://failed1.com", status=LinkStatus.FAILED),
        ]

        await link_reader.links_repo.save_links(
            entity_name, group, test_date, test_links
        )
        return test_links

    @pytest.mark.asyncio
    async def test_execute_returns_all_links_without_filter(
        self, link_reader, mock_logger
    ):
        # Arrange
        entity_name = "BR"
        group = "DOU1"
        test_date = date(2023, 2, 15)

        # Populate test data
        expected_links = await self._populate_test_links(
            link_reader, entity_name, group, test_date
        )

        # Act
        result = await link_reader.execute(entity_name, group, test_date)

        # Assert
        assert len(result) == 5

        # Verify all links are returned
        result_urls = [link.link for link in result]
        expected_urls = [link.link for link in expected_links]

        for expected_url in expected_urls:
            assert expected_url in result_urls

        # Verify all are Link objects with correct attributes
        for link in result:
            assert isinstance(link, Link)
            assert hasattr(link, "link")
            assert hasattr(link, "status")
            assert isinstance(link.status, LinkStatus)

        # Verify logging
        mock_logger.info.assert_called_once_with(
            f"Retrieved 5 links for {entity_name}:{group} on {test_date}"
        )

    @pytest.mark.asyncio
    async def test_execute_filters_by_pending_status(self, link_reader, mock_logger):
        # Arrange
        entity_name = "BR"
        group = "DOU1"
        test_date = date(2023, 2, 15)

        await self._populate_test_links(link_reader, entity_name, group, test_date)

        # Act
        result = await link_reader.execute(
            entity_name, group, test_date, LinkStatus.PENDING
        )

        # Assert
        assert len(result) == 2  # Only 2 pending links

        # All returned links should be pending
        for link in result:
            assert link.status == LinkStatus.PENDING

        # Verify specific URLs
        result_urls = [link.link for link in result]
        assert "https://pending1.com" in result_urls
        assert "https://pending2.com" in result_urls

        # Should not contain processed or failed links
        assert "https://processed1.com" not in result_urls
        assert "https://failed1.com" not in result_urls

        # Verify logging
        mock_logger.info.assert_called_once_with(
            f"Retrieved 2 pending links for {entity_name}:{group} on {test_date}"
        )

    @pytest.mark.asyncio
    async def test_execute_filters_by_processed_status(self, link_reader, mock_logger):
        # Arrange
        entity_name = "BR"
        group = "DOU1"
        test_date = date(2023, 2, 15)

        await self._populate_test_links(link_reader, entity_name, group, test_date)

        # Act
        result = await link_reader.execute(
            entity_name, group, test_date, LinkStatus.PROCESSED
        )

        # Assert
        assert len(result) == 2  # Only 2 processed links

        # All returned links should be processed
        for link in result:
            assert link.status == LinkStatus.PROCESSED

        # Verify specific URLs
        result_urls = [link.link for link in result]
        assert "https://processed1.com" in result_urls
        assert "https://processed2.com" in result_urls

        # Verify logging
        mock_logger.info.assert_called_once_with(
            f"Retrieved 2 processed links for {entity_name}:{group} on {test_date}"
        )

    @pytest.mark.asyncio
    async def test_execute_filters_by_failed_status(self, link_reader, mock_logger):
        # Arrange
        entity_name = "BR"
        group = "DOU1"
        test_date = date(2023, 2, 15)

        await self._populate_test_links(link_reader, entity_name, group, test_date)

        # Act
        result = await link_reader.execute(
            entity_name, group, test_date, LinkStatus.FAILED
        )

        # Assert
        assert len(result) == 1  # Only 1 failed link

        # The returned link should be failed
        assert result[0].status == LinkStatus.FAILED
        assert result[0].link == "https://failed1.com"

        # Verify logging
        mock_logger.info.assert_called_once_with(
            f"Retrieved 1 failed links for {entity_name}:{group} on {test_date}"
        )

    @pytest.mark.asyncio
    async def test_execute_returns_empty_list_for_nonexistent_data(
        self, link_reader, mock_logger
    ):
        # Arrange
        entity_name = "NONEXISTENT"
        group = "NONEXISTENT"
        test_date = date(2023, 2, 15)

        # Act - Try to get links without saving any
        result = await link_reader.execute(entity_name, group, test_date)

        # Assert
        assert result == []

        # Verify logging
        mock_logger.info.assert_called_once_with(
            f"Retrieved 0 links for {entity_name}:{group} on {test_date}"
        )

    @pytest.mark.asyncio
    async def test_execute_returns_empty_list_when_no_matches_for_filter(
        self, link_reader, mock_logger
    ):
        # Arrange
        entity_name = "BR"
        group = "DOU1"
        test_date = date(2023, 2, 15)

        # Only add pending links
        pending_links = [
            Link(link="https://pending1.com", status=LinkStatus.PENDING),
            Link(link="https://pending2.com", status=LinkStatus.PENDING),
        ]
        await link_reader.links_repo.save_links(
            entity_name, group, test_date, pending_links
        )

        # Act - Filter by processed status (should find none)
        result = await link_reader.execute(
            entity_name, group, test_date, LinkStatus.PROCESSED
        )

        # Assert
        assert result == []

        # Verify logging
        mock_logger.info.assert_called_once_with(
            f"Retrieved 0 processed links for {entity_name}:{group} on {test_date}"
        )

    @pytest.mark.asyncio
    async def test_execute_with_different_entity_group_combinations(
        self, link_reader, mock_logger
    ):
        # Arrange
        entity1, group1 = "BR", "DOU1"
        entity2, group2 = "US", "GOV"
        test_date = date(2023, 2, 15)

        # Add different links for different entity/group combinations
        links1 = [Link(link="https://br-link1.com", status=LinkStatus.PENDING)]
        links2 = [Link(link="https://us-link1.com", status=LinkStatus.PROCESSED)]

        await link_reader.links_repo.save_links(entity1, group1, test_date, links1)
        await link_reader.links_repo.save_links(entity2, group2, test_date, links2)

        # Act
        result1 = await link_reader.execute(entity1, group1, test_date)
        result2 = await link_reader.execute(entity2, group2, test_date)

        # Assert
        assert len(result1) == 1
        assert len(result2) == 1

        assert result1[0].link == "https://br-link1.com"
        assert result1[0].status == LinkStatus.PENDING

        assert result2[0].link == "https://us-link1.com"
        assert result2[0].status == LinkStatus.PROCESSED

    @pytest.mark.asyncio
    async def test_execute_with_different_dates(self, link_reader, mock_logger):
        # Arrange
        entity_name = "BR"
        group = "DOU1"
        date1 = date(2023, 2, 15)
        date2 = date(2023, 2, 16)

        # Add different links for different dates
        links1 = [Link(link="https://link-15.com", status=LinkStatus.PENDING)]
        links2 = [Link(link="https://link-16.com", status=LinkStatus.PROCESSED)]

        await link_reader.links_repo.save_links(entity_name, group, date1, links1)
        await link_reader.links_repo.save_links(entity_name, group, date2, links2)

        # Act
        result1 = await link_reader.execute(entity_name, group, date1)
        result2 = await link_reader.execute(entity_name, group, date2)

        # Assert
        assert len(result1) == 1
        assert len(result2) == 1

        assert result1[0].link == "https://link-15.com"
        assert result2[0].link == "https://link-16.com"

    @pytest.mark.asyncio
    async def test_execute_with_large_dataset(self, link_reader, mock_logger):
        # Arrange
        entity_name = "BR"
        group = "DOU1"
        test_date = date(2023, 2, 15)

        # Create a large dataset with mixed statuses
        large_dataset = []
        for i in range(100):
            if i % 3 == 0:
                status = LinkStatus.PENDING
            elif i % 3 == 1:
                status = LinkStatus.PROCESSED
            else:
                status = LinkStatus.FAILED

            large_dataset.append(Link(link=f"https://link{i}.com", status=status))

        await link_reader.links_repo.save_links(
            entity_name, group, test_date, large_dataset
        )

        # Act - Get all links
        all_results = await link_reader.execute(entity_name, group, test_date)

        # Act - Get only pending links
        pending_results = await link_reader.execute(
            entity_name, group, test_date, LinkStatus.PENDING
        )

        # Assert
        assert len(all_results) == 100
        assert len(pending_results) == 34  # Roughly 1/3 of 100 (indices 0, 3, 6, ...)

        # Verify all pending results have correct status
        for link in pending_results:
            assert link.status == LinkStatus.PENDING

    @pytest.mark.asyncio
    async def test_execute_error_handling_and_logging(self, mock_logger):
        # Arrange - Create LinkReader with a mock repo that raises an exception
        from unittest.mock import AsyncMock

        mock_repo = AsyncMock()
        mock_repo.get_links.side_effect = Exception("Database connection failed")

        link_reader = LinkReader(links_repo=mock_repo, logger=mock_logger)

        entity_name = "BR"
        group = "DOU1"
        test_date = date(2023, 2, 15)

        # Act & Assert
        with pytest.raises(Exception, match="Database connection failed"):
            await link_reader.execute(entity_name, group, test_date)

        # Verify error logging
        mock_logger.error.assert_called_once_with(
            f"Error reading links for {entity_name}:{group} on {test_date}: Database connection failed"
        )

    def test_link_reader_initialization(self, db_session, mock_logger):
        # Act
        reader = LinkReader(links_repo=LinksRepo(db_session), logger=mock_logger)

        # Assert
        assert isinstance(reader.links_repo, LinksRepo)
        assert reader.logger == mock_logger

    @pytest.mark.asyncio
    async def test_execute_mixed_status_filtering(self, link_reader, mock_logger):
        # Arrange
        entity_name = "BR"
        group = "DOU1"
        test_date = date(2023, 2, 15)

        # Create a mix of statuses with multiple links of each type
        mixed_links = [
            Link(link="https://pending1.com", status=LinkStatus.PENDING),
            Link(link="https://processed1.com", status=LinkStatus.PROCESSED),
            Link(link="https://failed1.com", status=LinkStatus.FAILED),
            Link(link="https://pending2.com", status=LinkStatus.PENDING),
            Link(link="https://processed2.com", status=LinkStatus.PROCESSED),
            Link(link="https://pending3.com", status=LinkStatus.PENDING),
        ]

        await link_reader.links_repo.save_links(
            entity_name, group, test_date, mixed_links
        )

        # Act - Test each filter type
        all_results = await link_reader.execute(entity_name, group, test_date)
        pending_results = await link_reader.execute(
            entity_name, group, test_date, LinkStatus.PENDING
        )
        processed_results = await link_reader.execute(
            entity_name, group, test_date, LinkStatus.PROCESSED
        )
        failed_results = await link_reader.execute(
            entity_name, group, test_date, LinkStatus.FAILED
        )

        # Assert
        assert len(all_results) == 6
        assert len(pending_results) == 3
        assert len(processed_results) == 2
        assert len(failed_results) == 1

        # Verify filtering correctness
        assert all(link.status == LinkStatus.PENDING for link in pending_results)
        assert all(link.status == LinkStatus.PROCESSED for link in processed_results)
        assert all(link.status == LinkStatus.FAILED for link in failed_results)

        # Verify specific URLs for each status
        pending_urls = [link.link for link in pending_results]
        processed_urls = [link.link for link in processed_results]
        failed_urls = [link.link for link in failed_results]

        assert "https://pending1.com" in pending_urls
        assert "https://pending2.com" in pending_urls
        assert "https://pending3.com" in pending_urls

        assert "https://processed1.com" in processed_urls
        assert "https://processed2.com" in processed_urls

        assert "https://failed1.com" in failed_urls
