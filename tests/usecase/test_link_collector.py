import json
import logging
from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from dou.app.gateway.links import IGetLink, IGetLinkRegistry
from dou.app.usecase.getlinks import LinkCollector
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


class TestLinkCollector:

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
        links = test_links_data["links"][:10]  # Use first 10 links for testing

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
    def link_collector(self, mock_registry, db_session, mock_logger):
        """Create LinkCollector using DI container with test dependencies"""
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

        return container.inject("link_collector")

    @pytest.mark.asyncio
    async def test_execute_with_commit_saves_links_to_database(
        self, link_collector, test_links_data, mock_logger
    ):
        # Arrange
        entity_name = test_links_data["entity"]
        group = test_links_data["group"]
        test_date = date(2023, 2, 11)
        commit = True

        # Act
        result = await link_collector.execute(entity_name, group, test_date, commit)

        # Assert
        expected_links = test_links_data["links"][:10]  # First 10 links
        assert result == expected_links

        # Verify links were saved to database
        saved_links = await link_collector.links_repo.get_links(
            entity_name, group, test_date
        )
        assert len(saved_links) == len(expected_links)

        saved_urls = [link.link for link in saved_links]
        saved_statuses = [link.status for link in saved_links]

        for expected_link in expected_links:
            assert expected_link in saved_urls
        assert all(status == LinkStatus.PENDING for status in saved_statuses)

        # Verify logging
        expected_calls = [
            f"Collected {len(expected_links)} links for {entity_name}:{group} on {test_date}",
            f"Saved {len(expected_links)} new links for {entity_name}:{group} on {test_date}",
        ]
        assert mock_logger.info.call_count == 2
        actual_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert actual_calls == expected_calls

    @pytest.mark.asyncio
    async def test_execute_without_commit_does_not_save_to_database(
        self, link_collector, test_links_data, mock_logger
    ):
        # Arrange
        entity_name = test_links_data["entity"]
        group = test_links_data["group"]
        test_date = date(2023, 2, 11)
        commit = False

        # Act
        result = await link_collector.execute(entity_name, group, test_date, commit)

        # Assert
        expected_links = test_links_data["links"][:10]
        assert result == expected_links

        # Verify links were NOT saved to database
        saved_links = await link_collector.links_repo.get_links(
            entity_name, group, test_date
        )
        assert saved_links == []

        # Verify logging
        mock_logger.info.assert_called_once_with(
            f"Collected {len(expected_links)} links for {entity_name}:{group} on {test_date}"
        )

    @pytest.mark.asyncio
    async def test_execute_with_different_entity_group_combinations(
        self, link_collector, mock_logger
    ):
        # Arrange
        entity_name = "test_entity"
        group = "test_group"
        test_date = date(2023, 3, 15)
        commit = True

        # Act
        result = await link_collector.execute(entity_name, group, test_date, commit)

        # Assert
        expected_links = ["https://test1.com", "https://test2.com"]
        assert result == expected_links

        # Verify links were saved
        saved_links = await link_collector.links_repo.get_links(
            entity_name, group, test_date
        )
        assert len(saved_links) == 2
        assert saved_links[0].link in expected_links
        assert saved_links[1].link in expected_links

    @pytest.mark.asyncio
    async def test_execute_raises_error_for_unregistered_collector(
        self, link_collector, mock_logger
    ):
        # Arrange
        entity_name = "nonexistent_entity"
        group = "nonexistent_group"
        test_date = date(2023, 1, 1)
        commit = False

        # Act & Assert
        with pytest.raises(
            ValueError,
            match="No link collector registered for nonexistent_entity:nonexistent_group",
        ):
            await link_collector.execute(entity_name, group, test_date, commit)

        # Verify error logging
        mock_logger.error.assert_called_once_with(
            "No link collector registered for nonexistent_entity:nonexistent_group"
        )

    @pytest.mark.asyncio
    async def test_execute_handles_empty_links_list(
        self, mock_registry, db_session, mock_logger
    ):
        # Arrange
        empty_collector = MockLinkCollector([])
        mock_registry.add("empty_entity", "empty_group", empty_collector)

        # Create LinkCollector using DI container
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

        link_collector = container.inject("link_collector")

        # Act
        result = await link_collector.execute(
            "empty_entity", "empty_group", date(2023, 1, 1), True
        )

        # Assert
        assert result == []

        # Verify empty entry was saved
        saved_links = await link_collector.links_repo.get_links(
            "empty_entity", "empty_group", date(2023, 1, 1)
        )
        assert saved_links == []

    @pytest.mark.asyncio
    async def test_execute_multiple_dates_same_entity_group(
        self, link_collector, test_links_data
    ):
        # Arrange
        entity_name = test_links_data["entity"]
        group = test_links_data["group"]
        test_date1 = date(2023, 2, 11)
        test_date2 = date(2023, 2, 12)

        # Act
        result1 = await link_collector.execute(entity_name, group, test_date1, True)
        result2 = await link_collector.execute(entity_name, group, test_date2, True)

        # Assert
        expected_links = test_links_data["links"][:10]
        assert result1 == expected_links
        assert result2 == expected_links  # Same collector returns same links

        # Verify both entries exist separately in database
        saved_links1 = await link_collector.links_repo.get_links(
            entity_name, group, test_date1
        )
        saved_links2 = await link_collector.links_repo.get_links(
            entity_name, group, test_date2
        )

        assert len(saved_links1) == len(expected_links)
        assert len(saved_links2) == len(expected_links)

    @pytest.mark.asyncio
    async def test_execute_with_large_links_collection(
        self, mock_registry, db_session, mock_logger, test_links_data
    ):
        # Arrange - Use all links from test data
        entity_name = "large_entity"
        group = "large_group"
        all_links = test_links_data["links"]  # All links from the file

        large_collector = MockLinkCollector(all_links)
        mock_registry.add(entity_name, group, large_collector)

        # Create LinkCollector using DI container
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

        link_collector = container.inject("link_collector")

        # Act
        result = await link_collector.execute(
            entity_name, group, date(2023, 1, 1), True
        )

        # Assert
        assert len(result) == len(all_links)
        assert result == all_links

        # Verify all links were saved
        saved_links = await link_collector.links_repo.get_links(
            entity_name, group, date(2023, 1, 1)
        )
        assert len(saved_links) == len(all_links)

    def test_link_collector_initialization(
        self, mock_registry, db_session, mock_logger
    ):
        # Act
        collector = LinkCollector(
            registry=mock_registry, links_repo=LinksRepo(db_session), logger=mock_logger
        )

        # Assert
        assert collector.registry == mock_registry
        assert isinstance(collector.links_repo, LinksRepo)
        assert collector.logger == mock_logger
