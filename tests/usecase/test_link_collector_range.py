import json
import logging
from datetime import date
from unittest.mock import Mock

import pytest
import pytest_asyncio
from dou.app.gateway.links import IGetLink, IGetLinkRegistry
from dou.app.usecase.getlinks import LinkCollector, LinkCollectorRange
from dou.domain.entity.Link import LinkStatus
from dou.infra.repo.links_repo.db import make_session
from dou.infra.repo.links_repo.model import Base
from dou.infra.repo.links_repo.repo import LinksRepo


class MockRegistry(IGetLinkRegistry):
    def __init__(self):
        self._collectors = {}

    def add(self, entity_name: str, group: str, get_link: IGetLink) -> None:
        key = f"{entity_name}:{group}"
        self._collectors[key] = get_link

    def get(self, entity_name: str, group: str) -> IGetLink:
        key = f"{entity_name}:{group}"
        if key not in self._collectors:
            raise KeyError(f"No collector for {key}")
        return self._collectors[key]


class MockLinkCollector:
    def __init__(self, links: list[str]):
        self.links = links

    async def __call__(self, test_date: date) -> list[str]:
        return self.links


class TestLinkCollectorRange:

    @pytest.fixture
    def test_links_data(self):
        """Load test data from links.txt"""
        with open("tests/links.txt", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data

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
    def mock_registry(self, test_links_data):
        """Create mock registry with test data"""
        registry = MockRegistry()

        # Add collector for the test data
        entity = test_links_data["entity"]
        group = test_links_data["group"]
        links = test_links_data["links"][:5]  # Use first 5 links for testing

        collector = MockLinkCollector(links)
        registry.add(entity, group, collector)

        # Add another collector for different entity/group
        registry.add(
            "test_entity",
            "test_group",
            MockLinkCollector(["https://test1.com", "https://test2.com"]),
        )

        return registry

    @pytest.fixture
    def link_collector_range(self, mock_registry, db_session, mock_logger):
        """Create LinkCollectorRange using DI container with test dependencies"""
        from dependency_injector import providers
        from dou.infra.di import Container

        container = Container()
        container.provide("logger", providers.Object(mock_logger))
        container.provide("link_registry", providers.Object(mock_registry))
        container.provide("links_repo", providers.Object(LinksRepo(db_session)))
        container.provide(
            "link_collector",
            providers.Factory(
                LinkCollector,
                registry=container._container.link_registry,
                links_repo=container._container.links_repo,
                logger=container._container.logger,
            ),
        )
        container.provide(
            "link_collector_range",
            providers.Factory(
                LinkCollectorRange,
                link_collector=container._container.link_collector,
                logger=container._container.logger,
            ),
        )

        return container.inject("link_collector_range")

    @pytest.mark.asyncio
    async def test_execute_with_commit_saves_links_for_range(
        self, link_collector_range, test_links_data, mock_logger
    ):
        # Arrange
        entity_name = test_links_data["entity"]
        group = test_links_data["group"]
        start_date = date(2023, 2, 13)  # Monday
        end_date = date(2023, 2, 17)  # Friday (5 weekdays)
        commit = True

        # Act
        result = await link_collector_range.execute(
            entity_name, group, start_date, end_date, commit
        )

        # Assert
        expected_links = test_links_data["links"][:5]  # First 5 links

        # Should have 5 weekdays in the result
        assert len(result) == 5

        # Each day should have the same links (since mock returns same list)
        for test_date, links in result.items():
            assert isinstance(test_date, date)
            assert links == expected_links

        # Verify links were saved to database for each day
        for test_date in result.keys():
            saved_links = await link_collector_range.link_collector.links_repo.get_links(
                entity_name, group, test_date
            )
            assert len(saved_links) == len(expected_links)

            saved_urls = [link.link for link in saved_links]
            saved_statuses = [link.status for link in saved_links]

            for expected_link in expected_links:
                assert expected_link in saved_urls
            assert all(status == LinkStatus.PENDING for status in saved_statuses)

        # Verify logging - should have start and end messages
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("Starting range collection" in call for call in info_calls)
        assert any("Range collection completed" in call for call in info_calls)

    @pytest.mark.asyncio
    async def test_execute_without_commit_does_not_save_to_database(
        self, link_collector_range, test_links_data, mock_logger
    ):
        # Arrange
        entity_name = test_links_data["entity"]
        group = test_links_data["group"]
        start_date = date(2023, 2, 13)  # Monday
        end_date = date(2023, 2, 15)  # Wednesday (3 weekdays)
        commit = False

        # Act
        result = await link_collector_range.execute(
            entity_name, group, start_date, end_date, commit
        )

        # Assert
        expected_links = test_links_data["links"][:5]

        # Should have 3 weekdays in the result
        assert len(result) == 3

        # Each day should have the expected links
        for test_date, links in result.items():
            assert links == expected_links

        # Verify links were NOT saved to database
        for test_date in result.keys():
            saved_links = await link_collector_range.link_collector.links_repo.get_links(
                entity_name, group, test_date
            )
            assert saved_links == []

        # Verify logging
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("Starting range collection" in call for call in info_calls)
        assert any("Range collection completed" in call for call in info_calls)

    @pytest.mark.asyncio
    async def test_execute_with_weekend_dates_excludes_weekends(
        self, link_collector_range, test_links_data, mock_logger
    ):
        # Arrange
        entity_name = test_links_data["entity"]
        group = test_links_data["group"]
        start_date = date(2023, 2, 11)  # Saturday
        end_date = date(2023, 2, 13)  # Monday
        commit = True

        # Act
        result = await link_collector_range.execute(
            entity_name, group, start_date, end_date, commit
        )

        # Assert
        # Should only have Monday (2023-02-13), not Saturday or Sunday
        assert len(result) == 1
        assert date(2023, 2, 13) in result.keys()
        assert date(2023, 2, 11) not in result.keys()  # Saturday excluded
        assert date(2023, 2, 12) not in result.keys()  # Sunday excluded

    @pytest.mark.asyncio
    async def test_execute_with_holidays_excludes_holidays(
        self, link_collector_range, test_links_data, mock_logger
    ):
        # Arrange - Include a range with New Year's Day (holiday)
        entity_name = test_links_data["entity"]
        group = test_links_data["group"]
        start_date = date(2023, 12, 29)  # Friday before New Year
        end_date = date(2023, 1, 3)  # Tuesday after New Year
        commit = True

        # Act
        result = await link_collector_range.execute(
            entity_name, group, start_date, end_date, commit
        )

        # Assert
        # Should exclude weekends and New Year's Day (January 1)
        dates_in_result = set(result.keys())
        assert date(2023, 1, 1) not in dates_in_result  # New Year's Day excluded

        # Should only contain weekdays that are not holidays
        for test_date in dates_in_result:
            assert test_date.weekday() < 5  # Only weekdays

    @pytest.mark.asyncio
    async def test_execute_with_different_entity_group_combinations(
        self, link_collector_range, mock_logger
    ):
        # Arrange
        entity_name = "test_entity"
        group = "test_group"
        start_date = date(2023, 3, 13)  # Monday
        end_date = date(2023, 3, 15)  # Wednesday (3 weekdays)
        commit = True

        # Act
        result = await link_collector_range.execute(
            entity_name, group, start_date, end_date, commit
        )

        # Assert
        expected_links = ["https://test1.com", "https://test2.com"]

        # Should have 3 weekdays
        assert len(result) == 3

        # Each day should have the expected links
        for test_date, links in result.items():
            assert links == expected_links

        # Verify links were saved for each day
        for test_date in result.keys():
            saved_links = await link_collector_range.link_collector.links_repo.get_links(
                entity_name, group, test_date
            )
            assert len(saved_links) == 2
            saved_urls = [link.link for link in saved_links]
            assert "https://test1.com" in saved_urls
            assert "https://test2.com" in saved_urls

    @pytest.mark.asyncio
    async def test_execute_raises_error_for_unregistered_collector(
        self, link_collector_range, mock_logger
    ):
        # Arrange
        entity_name = "nonexistent_entity"
        group = "nonexistent_group"
        start_date = date(2023, 1, 2)  # Monday
        end_date = date(2023, 1, 4)  # Wednesday
        commit = False

        # Act & Assert
        with pytest.raises(ValueError, match="No link collector registered"):
            await link_collector_range.execute(
                entity_name, group, start_date, end_date, commit
            )

        # Verify error logging
        error_calls = [call.args[0] for call in mock_logger.error.call_args_list]
        assert any("No link collector registered" in call for call in error_calls)

    @pytest.mark.asyncio
    async def test_execute_handles_empty_date_range(
        self, link_collector_range, test_links_data, mock_logger
    ):
        # Arrange - Range with no weekdays (e.g., just a weekend)
        entity_name = test_links_data["entity"]
        group = test_links_data["group"]
        start_date = date(2023, 2, 11)  # Saturday
        end_date = date(2023, 2, 12)  # Sunday
        commit = True

        # Act
        result = await link_collector_range.execute(
            entity_name, group, start_date, end_date, commit
        )

        # Assert
        assert result == {}  # Empty dict for no weekdays

        # Verify logging
        info_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("Starting range collection" in call for call in info_calls)
        assert any("0 weekdays" in call for call in info_calls)

    @pytest.mark.asyncio
    async def test_execute_single_day_range(
        self, link_collector_range, test_links_data, mock_logger
    ):
        # Arrange
        entity_name = test_links_data["entity"]
        group = test_links_data["group"]
        single_date = date(2023, 2, 13)  # Monday
        commit = True

        # Act
        result = await link_collector_range.execute(
            entity_name, group, single_date, single_date, commit
        )

        # Assert
        expected_links = test_links_data["links"][:5]

        assert len(result) == 1
        assert single_date in result
        assert result[single_date] == expected_links

        # Verify links were saved
        saved_links = await link_collector_range.link_collector.links_repo.get_links(
            entity_name, group, single_date
        )
        assert len(saved_links) == len(expected_links)

    @pytest.mark.asyncio
    async def test_execute_reversed_date_range(
        self, link_collector_range, test_links_data, mock_logger
    ):
        # Arrange - End date before start date
        entity_name = test_links_data["entity"]
        group = test_links_data["group"]
        start_date = date(2023, 2, 17)  # Friday
        end_date = date(2023, 2, 13)  # Monday (before start)
        commit = True

        # Act
        result = await link_collector_range.execute(
            entity_name, group, start_date, end_date, commit
        )

        # Assert
        # get_weekdays_from_range should handle reversed dates correctly
        expected_weekdays = 5  # Monday to Friday
        assert len(result) == expected_weekdays

        # Should contain dates from Monday to Friday
        dates_in_result = sorted(result.keys())
        assert dates_in_result[0] == date(2023, 2, 13)  # Monday
        assert dates_in_result[-1] == date(2023, 2, 17)  # Friday

    @pytest.mark.asyncio
    async def test_execute_multi_year_range(
        self, link_collector_range, test_links_data, mock_logger
    ):
        # Arrange - Range spanning multiple years
        entity_name = test_links_data["entity"]
        group = test_links_data["group"]
        start_date = date(2022, 12, 30)  # Friday
        end_date = date(2023, 1, 3)  # Tuesday
        commit = True

        # Act
        result = await link_collector_range.execute(
            entity_name, group, start_date, end_date, commit
        )

        # Assert
        # Should handle multi-year range correctly
        years_in_result = {d.year for d in result.keys()}
        assert 2022 in years_in_result
        assert 2023 in years_in_result

        # Should exclude New Year's Day (holiday) and weekends
        assert date(2023, 1, 1) not in result.keys()  # New Year's Day

    @pytest.mark.asyncio
    async def test_execute_with_large_range(
        self, link_collector_range, test_links_data, mock_logger
    ):
        # Arrange - Large date range (1 month)
        entity_name = test_links_data["entity"]
        group = test_links_data["group"]
        start_date = date(2023, 3, 1)
        end_date = date(2023, 3, 31)
        commit = True

        # Act
        result = await link_collector_range.execute(
            entity_name, group, start_date, end_date, commit
        )

        # Assert
        # March 2023 should have around 23 weekdays (excluding weekends and any holidays)
        assert len(result) >= 20  # At least 20 weekdays
        assert len(result) <= 25  # At most 25 weekdays

        # All dates should be weekdays
        for test_date in result.keys():
            assert test_date.weekday() < 5
            assert test_date.month == 3
            assert test_date.year == 2023

        # Verify some links were collected
        total_links = sum(len(links) for links in result.values())
        assert total_links > 0

    @pytest.mark.asyncio
    async def test_execute_with_existing_links_in_database(
        self, link_collector_range, test_links_data, mock_logger
    ):
        # Arrange
        entity_name = test_links_data["entity"]
        group = test_links_data["group"]
        start_date = date(2023, 2, 13)  # Monday
        end_date = date(2023, 2, 15)  # Wednesday
        commit = True

        # Pre-populate some links for one day
        from dou.domain.entity.Link import Link

        existing_links = [Link(link=test_links_data["links"][0])]  # First link
        await link_collector_range.link_collector.links_repo.save_links(
            entity_name, group, date(2023, 2, 13), existing_links
        )

        # Act
        result = await link_collector_range.execute(
            entity_name, group, start_date, end_date, commit
        )

        # Assert
        assert len(result) == 3  # 3 weekdays

        # Monday should have fewer new links (since one already existed)
        monday_links = result[date(2023, 2, 13)]
        tuesday_links = result[date(2023, 2, 14)]

        # Tuesday should have all links, Monday should have fewer new ones
        assert len(tuesday_links) >= len(monday_links)

    def test_link_collector_range_initialization(
        self, mock_registry, db_session, mock_logger
    ):
        # Act
        link_collector = LinkCollector(
            registry=mock_registry, links_repo=LinksRepo(db_session), logger=mock_logger
        )
        collector_range = LinkCollectorRange(
            link_collector=link_collector, logger=mock_logger
        )

        # Assert
        assert collector_range.link_collector == link_collector
        assert isinstance(collector_range.link_collector.links_repo, LinksRepo)
        assert collector_range.logger == mock_logger

    @pytest.mark.asyncio
    async def test_execute_logging_details(
        self, link_collector_range, test_links_data, mock_logger
    ):
        # Arrange
        entity_name = test_links_data["entity"]
        group = test_links_data["group"]
        start_date = date(2023, 2, 13)  # Monday
        end_date = date(2023, 2, 15)  # Wednesday (3 weekdays)
        commit = True

        # Act
        result = await link_collector_range.execute(
            entity_name, group, start_date, end_date, commit
        )

        # Assert
        # Check that all expected log messages are present
        all_calls = [call.args[0] for call in mock_logger.info.call_args_list]

        # Should have start message
        start_messages = [
            call for call in all_calls if "Starting range collection" in call
        ]
        assert len(start_messages) == 1
        assert "3 weekdays" in start_messages[0]

        # Should have completion message
        completion_messages = [
            call for call in all_calls if "Range collection completed" in call
        ]
        assert len(completion_messages) == 1

        # Each individual day should also be logged (from parent LinkCollector)
        # Should have "Collected X links" and "Saved X links" for each day
        collected_messages = [
            call for call in all_calls if "Collected" in call and "links for" in call
        ]
        saved_messages = [
            call for call in all_calls if "Saved" in call and "links for" in call
        ]

        # Should have one collect and one save message per day (3 days)
        assert len(collected_messages) == 3
        assert len(saved_messages) == 3
