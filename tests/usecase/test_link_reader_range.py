import logging
from datetime import date
from unittest.mock import Mock

import pytest
import pytest_asyncio
from dou.app.usecase.readlinks import LinkReader, LinkReaderRange
from dou.domain.entity.Link import Link, LinkStatus
from dou.infra.repo.links_repo.db import make_session
from dou.infra.repo.links_repo.model import Base
from dou.infra.repo.links_repo.repo import LinksRepo


class TestLinkReaderRange:

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
    def link_reader_range(self, db_session, mock_logger):
        """Create LinkReaderRange using DI container with test dependencies"""
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
        container.provide(
            "link_reader_range",
            providers.Factory(
                LinkReaderRange,
                link_reader=container._container.link_reader,
                logger=container._container.logger,
            ),
        )

        return container.inject("link_reader_range")

    async def _populate_test_links(
        self, link_reader_range, entity_name: str, group: str, test_date: date, links: list[Link]
    ):
        """Helper method to populate test data"""
        await link_reader_range.link_reader.links_repo.save_links(
            entity_name, group, test_date, links
        )
        return links

    @pytest.mark.asyncio
    async def test_execute_returns_all_links_for_weekday_range(
        self, link_reader_range, mock_logger
    ):
        # Arrange
        entity_name = "BR"
        group = "DOU1"
        start_date = date(2023, 2, 13)  # Monday
        end_date = date(2023, 2, 17)    # Friday
        
        # Create test data for each weekday
        monday_links = [
            Link(link="https://monday1.com", status=LinkStatus.PENDING),
            Link(link="https://monday2.com", status=LinkStatus.PROCESSED),
        ]
        tuesday_links = [
            Link(link="https://tuesday1.com", status=LinkStatus.PENDING),
        ]
        wednesday_links = [
            Link(link="https://wednesday1.com", status=LinkStatus.FAILED),
            Link(link="https://wednesday2.com", status=LinkStatus.PROCESSED),
        ]
        
        # Populate test data
        await self._populate_test_links(link_reader_range, entity_name, group, date(2023, 2, 13), monday_links)
        await self._populate_test_links(link_reader_range, entity_name, group, date(2023, 2, 14), tuesday_links)
        await self._populate_test_links(link_reader_range, entity_name, group, date(2023, 2, 15), wednesday_links)

        # Act
        result = await link_reader_range.execute(entity_name, group, start_date, end_date)

        # Assert
        assert len(result) == 5  # 5 weekdays (Mon-Fri)
        
        # Verify Monday results
        assert len(result[date(2023, 2, 13)]) == 2
        assert len(result[date(2023, 2, 14)]) == 1
        assert len(result[date(2023, 2, 15)]) == 2
        assert len(result[date(2023, 2, 16)]) == 0  # No data for Thursday
        assert len(result[date(2023, 2, 17)]) == 0  # No data for Friday

        # Verify all are Link objects with correct attributes
        for date_key, links in result.items():
            for link in links:
                assert isinstance(link, Link)
                assert hasattr(link, "link")
                assert hasattr(link, "status")
                assert isinstance(link.status, LinkStatus)

        # Verify logging calls
        assert mock_logger.info.call_count >= 2  # Start and completion logs

    @pytest.mark.asyncio
    async def test_execute_filters_by_pending_status_across_range(
        self, link_reader_range, mock_logger
    ):
        # Arrange
        entity_name = "BR"
        group = "DOU1"
        start_date = date(2023, 2, 13)  # Monday
        end_date = date(2023, 2, 15)    # Wednesday
        
        # Mix of statuses across different days
        monday_links = [
            Link(link="https://pending1.com", status=LinkStatus.PENDING),
            Link(link="https://processed1.com", status=LinkStatus.PROCESSED),
        ]
        tuesday_links = [
            Link(link="https://pending2.com", status=LinkStatus.PENDING),
            Link(link="https://failed1.com", status=LinkStatus.FAILED),
        ]
        wednesday_links = [
            Link(link="https://processed2.com", status=LinkStatus.PROCESSED),
        ]
        
        # Populate test data
        await self._populate_test_links(link_reader_range, entity_name, group, date(2023, 2, 13), monday_links)
        await self._populate_test_links(link_reader_range, entity_name, group, date(2023, 2, 14), tuesday_links)
        await self._populate_test_links(link_reader_range, entity_name, group, date(2023, 2, 15), wednesday_links)

        # Act
        result = await link_reader_range.execute(
            entity_name, group, start_date, end_date, LinkStatus.PENDING
        )

        # Assert
        assert len(result) == 3  # 3 weekdays
        
        # Only pending links should be returned
        assert len(result[date(2023, 2, 13)]) == 1  # 1 pending on Monday
        assert len(result[date(2023, 2, 14)]) == 1  # 1 pending on Tuesday
        assert len(result[date(2023, 2, 15)]) == 0  # 0 pending on Wednesday

        # Verify all returned links are pending
        for date_key, links in result.items():
            for link in links:
                assert link.status == LinkStatus.PENDING

    @pytest.mark.asyncio
    async def test_execute_handles_weekend_exclusion(
        self, link_reader_range, mock_logger
    ):
        # Arrange
        entity_name = "BR"
        group = "DOU1"
        start_date = date(2023, 2, 11)  # Saturday
        end_date = date(2023, 2, 13)    # Monday
        
        # Populate data for all days including weekend
        saturday_links = [Link(link="https://saturday.com", status=LinkStatus.PENDING)]
        sunday_links = [Link(link="https://sunday.com", status=LinkStatus.PENDING)]
        monday_links = [Link(link="https://monday.com", status=LinkStatus.PENDING)]
        
        await self._populate_test_links(link_reader_range, entity_name, group, date(2023, 2, 11), saturday_links)
        await self._populate_test_links(link_reader_range, entity_name, group, date(2023, 2, 12), sunday_links)
        await self._populate_test_links(link_reader_range, entity_name, group, date(2023, 2, 13), monday_links)

        # Act
        result = await link_reader_range.execute(entity_name, group, start_date, end_date)

        # Assert
        assert len(result) == 1  # Only Monday (weekday)
        assert date(2023, 2, 13) in result  # Monday should be included
        assert date(2023, 2, 11) not in result  # Saturday should be excluded
        assert date(2023, 2, 12) not in result  # Sunday should be excluded
        
        assert len(result[date(2023, 2, 13)]) == 1

    @pytest.mark.asyncio
    async def test_execute_returns_empty_results_for_nonexistent_data(
        self, link_reader_range, mock_logger
    ):
        # Arrange
        entity_name = "NONEXISTENT"
        group = "NONEXISTENT"
        start_date = date(2023, 2, 13)
        end_date = date(2023, 2, 17)

        # Act - Try to get links without saving any
        result = await link_reader_range.execute(entity_name, group, start_date, end_date)

        # Assert
        assert len(result) == 5  # 5 weekdays
        for date_key, links in result.items():
            assert links == []

    @pytest.mark.asyncio
    async def test_execute_handles_multi_week_range(
        self, link_reader_range, mock_logger
    ):
        # Arrange
        entity_name = "BR"
        group = "DOU1"
        start_date = date(2023, 2, 13)  # Monday week 1
        end_date = date(2023, 2, 24)    # Friday week 2
        
        # Populate some data across the range
        week1_links = [Link(link="https://week1.com", status=LinkStatus.PENDING)]
        week2_links = [Link(link="https://week2.com", status=LinkStatus.PROCESSED)]
        
        await self._populate_test_links(link_reader_range, entity_name, group, date(2023, 2, 13), week1_links)
        await self._populate_test_links(link_reader_range, entity_name, group, date(2023, 2, 22), week2_links)

        # Act
        result = await link_reader_range.execute(entity_name, group, start_date, end_date)

        # Assert
        expected_weekdays = 8  # Actual weekdays in range (excludes holidays)
        assert len(result) == expected_weekdays
        
        # Verify specific dates have data
        assert len(result[date(2023, 2, 13)]) == 1  # Week 1 Monday
        assert len(result[date(2023, 2, 22)]) == 1  # Week 2 Wednesday
        
        # Most other days should be empty
        empty_days = sum(1 for links in result.values() if len(links) == 0)
        assert empty_days == expected_weekdays - 2

    @pytest.mark.asyncio
    async def test_execute_with_different_entity_group_combinations(
        self, link_reader_range, mock_logger
    ):
        # Arrange
        entity1, group1 = "BR", "DOU1"
        entity2, group2 = "US", "GOV"
        start_date = date(2023, 2, 13)
        end_date = date(2023, 2, 15)

        # Add different links for different entity/group combinations
        links1 = [Link(link="https://br-link1.com", status=LinkStatus.PENDING)]
        links2 = [Link(link="https://us-link1.com", status=LinkStatus.PROCESSED)]

        await self._populate_test_links(link_reader_range, entity1, group1, date(2023, 2, 13), links1)
        await self._populate_test_links(link_reader_range, entity2, group2, date(2023, 2, 13), links2)

        # Act
        result1 = await link_reader_range.execute(entity1, group1, start_date, end_date)
        result2 = await link_reader_range.execute(entity2, group2, start_date, end_date)

        # Assert
        assert len(result1) == 3  # 3 weekdays
        assert len(result2) == 3  # 3 weekdays

        assert len(result1[date(2023, 2, 13)]) == 1
        assert len(result2[date(2023, 2, 13)]) == 1

        assert result1[date(2023, 2, 13)][0].link == "https://br-link1.com"
        assert result1[date(2023, 2, 13)][0].status == LinkStatus.PENDING

        assert result2[date(2023, 2, 13)][0].link == "https://us-link1.com"
        assert result2[date(2023, 2, 13)][0].status == LinkStatus.PROCESSED

    @pytest.mark.asyncio
    async def test_execute_error_handling_continues_processing(
        self, db_session, mock_logger
    ):
        # Arrange - Create LinkReaderRange with a mock repo that raises an exception for specific dates
        from unittest.mock import AsyncMock

        mock_repo = AsyncMock()
        
        # Make it fail for one specific date but succeed for others
        async def mock_get_links(entity, group, test_date):
            if test_date == date(2023, 2, 14):  # Tuesday fails
                raise Exception("Database connection failed")
            elif test_date == date(2023, 2, 13):  # Monday succeeds
                return [Link(link="https://monday.com", status=LinkStatus.PENDING)]
            else:
                return []

        mock_repo.get_links.side_effect = mock_get_links

        # Create a mock LinkReader with the failing repo
        mock_link_reader = LinkReader(links_repo=mock_repo, logger=mock_logger)
        link_reader_range = LinkReaderRange(link_reader=mock_link_reader, logger=mock_logger)

        entity_name = "BR"
        group = "DOU1"
        start_date = date(2023, 2, 13)  # Monday
        end_date = date(2023, 2, 15)    # Wednesday

        # Act - Should not raise exception despite one day failing
        result = await link_reader_range.execute(entity_name, group, start_date, end_date)

        # Assert
        assert len(result) == 3  # All 3 weekdays should be in result
        
        # Monday should have data, Tuesday should be empty (failed), Wednesday should be empty
        assert len(result[date(2023, 2, 13)]) == 1
        assert len(result[date(2023, 2, 14)]) == 0  # Failed day
        assert len(result[date(2023, 2, 15)]) == 0

        # Verify error logging for the failed day
        mock_logger.error.assert_called()

    def test_link_reader_range_initialization(self, db_session, mock_logger):
        # Act
        link_reader = LinkReader(links_repo=LinksRepo(db_session), logger=mock_logger)
        reader = LinkReaderRange(link_reader=link_reader, logger=mock_logger)

        # Assert
        assert reader.link_reader == link_reader
        assert isinstance(reader.link_reader.links_repo, LinksRepo)
        assert reader.logger == mock_logger

    @pytest.mark.asyncio
    async def test_execute_mixed_status_filtering_across_range(
        self, link_reader_range, mock_logger
    ):
        # Arrange
        entity_name = "BR"
        group = "DOU1"
        start_date = date(2023, 2, 13)
        end_date = date(2023, 2, 15)

        # Create different status mixes across days
        monday_links = [
            Link(link="https://mon-pending.com", status=LinkStatus.PENDING),
            Link(link="https://mon-processed.com", status=LinkStatus.PROCESSED),
            Link(link="https://mon-failed.com", status=LinkStatus.FAILED),
        ]
        tuesday_links = [
            Link(link="https://tue-pending.com", status=LinkStatus.PENDING),
            Link(link="https://tue-processed.com", status=LinkStatus.PROCESSED),
        ]
        wednesday_links = [
            Link(link="https://wed-failed.com", status=LinkStatus.FAILED),
        ]

        await self._populate_test_links(link_reader_range, entity_name, group, date(2023, 2, 13), monday_links)
        await self._populate_test_links(link_reader_range, entity_name, group, date(2023, 2, 14), tuesday_links)
        await self._populate_test_links(link_reader_range, entity_name, group, date(2023, 2, 15), wednesday_links)

        # Act - Test each filter type
        all_results = await link_reader_range.execute(entity_name, group, start_date, end_date)
        pending_results = await link_reader_range.execute(
            entity_name, group, start_date, end_date, LinkStatus.PENDING
        )
        processed_results = await link_reader_range.execute(
            entity_name, group, start_date, end_date, LinkStatus.PROCESSED
        )
        failed_results = await link_reader_range.execute(
            entity_name, group, start_date, end_date, LinkStatus.FAILED
        )

        # Assert totals
        total_all = sum(len(links) for links in all_results.values())
        total_pending = sum(len(links) for links in pending_results.values())
        total_processed = sum(len(links) for links in processed_results.values())
        total_failed = sum(len(links) for links in failed_results.values())

        assert total_all == 6  # 3 + 2 + 1
        assert total_pending == 2  # 1 Monday + 1 Tuesday
        assert total_processed == 2  # 1 Monday + 1 Tuesday
        assert total_failed == 2  # 1 Monday + 1 Wednesday

        # Verify filtering correctness
        for date_key, links in pending_results.items():
            assert all(link.status == LinkStatus.PENDING for link in links)
        for date_key, links in processed_results.items():
            assert all(link.status == LinkStatus.PROCESSED for link in links)
        for date_key, links in failed_results.items():
            assert all(link.status == LinkStatus.FAILED for link in links)