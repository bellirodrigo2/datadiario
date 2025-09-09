import pytest
import pytest_asyncio
from datetime import date
from unittest.mock import AsyncMock, patch
import logging

from src.app.usecase.getlinks import LinkCollector, LinkCollectorRange
from src.infra.repo.links_repo.repo import LinksRepo
from src.infra.repo.links_repo.db import make_session
from src.infra.repo.links_repo.model import Base
from src.domain.entity.Link import Link, LinkStatus


@pytest_asyncio.fixture
async def session_factory():
    """Create a session factory for testing."""
    db_url = "sqlite+aiosqlite:///:memory:"
    factory = await make_session(db_url, Base)
    yield factory


@pytest.fixture
def links_repo(session_factory):
    """Create a LinksRepo instance with the test database session factory."""
    return LinksRepo(session_factory)


@pytest.fixture
def logger():
    """Create a logger for testing."""
    return logging.getLogger("test")


@pytest.fixture
def mock_get_link():
    """Create a mock get_link function."""
    mock = AsyncMock()
    return mock


@pytest.fixture
def mock_registry(mock_get_link):
    """Create a mock registry with the get_link function."""
    return {"BR_FEDERAL:DOU1": mock_get_link}


@pytest.fixture
def link_collector(mock_registry, links_repo, logger):
    """Create a LinkCollector instance for testing."""
    return LinkCollector(
        registry=mock_registry,
        links_repo=links_repo,
        logger=logger
    )


@pytest.fixture
def link_collector_range(link_collector, logger):
    """Create a LinkCollectorRange instance for testing."""
    return LinkCollectorRange(
        link_collector=link_collector,
        logger=logger
    )


class TestLinkCollectorIntegration:
    """Integration tests for LinkCollector usecase."""

    @pytest.mark.asyncio
    async def test_execute_success_with_commit(self, link_collector, mock_get_link):
        """Test successful link collection with commit."""
        # Arrange
        entity_name = "br_federal"
        group = "dou1"
        target_date = date(2025, 1, 15)
        expected_links = [
            "https://example.com/link1",
            "https://example.com/link2",
            "https://example.com/link3"
        ]
        mock_get_link.return_value = expected_links

        # Act
        result = await link_collector.execute(entity_name, group, target_date, commit=True)

        # Assert
        assert result == expected_links
        mock_get_link.assert_called_once_with(target_date)
        
        # Verify links were saved to database
        saved_links = await link_collector.links_repo.get_links(entity_name, group, target_date)
        assert len(saved_links) == 3
        assert all(link.status == LinkStatus.PENDING for link in saved_links)
        assert [link.link for link in saved_links] == expected_links

    @pytest.mark.asyncio
    async def test_execute_success_without_commit(self, link_collector, mock_get_link):
        """Test successful link collection without commit."""
        # Arrange
        entity_name = "br_federal"
        group = "dou1"
        target_date = date(2025, 1, 15)
        expected_links = [
            "https://example.com/link1",
            "https://example.com/link2"
        ]
        mock_get_link.return_value = expected_links

        # Act
        result = await link_collector.execute(entity_name, group, target_date, commit=False)

        # Assert
        assert result == expected_links
        mock_get_link.assert_called_once_with(target_date)
        
        # Verify links were NOT saved to database
        saved_links = await link_collector.links_repo.get_links(entity_name, group, target_date)
        assert len(saved_links) == 0

    @pytest.mark.asyncio
    async def test_execute_with_existing_links(self, link_collector, mock_get_link):
        """Test link collection when some links already exist."""
        # Arrange
        entity_name = "br_federal"
        group = "dou1"
        target_date = date(2025, 1, 15)
        
        # First, save some existing links
        existing_links = [
            Link(link="https://example.com/existing1"),
            Link(link="https://example.com/existing2", status=LinkStatus.FAILED)
        ]
        await link_collector.links_repo.save_links(entity_name, group, target_date, existing_links)
        
        # Mock returns both existing and new links
        all_links = [
            "https://example.com/existing1",  # Already exists with PENDING status
            "https://example.com/existing2",  # Already exists with FAILED status (should retry)
            "https://example.com/new1",       # New link
            "https://example.com/new2"        # New link
        ]
        mock_get_link.return_value = all_links

        # Act
        result = await link_collector.execute(entity_name, group, target_date, commit=True)

        # Assert
        # Should return only new links and retry failed ones
        expected_new_links = [
            "https://example.com/existing2",  # Retry failed link
            "https://example.com/new1",
            "https://example.com/new2"
        ]
        assert result == expected_new_links
        
        # Verify database state
        saved_links = await link_collector.links_repo.get_links(entity_name, group, target_date)
        assert len(saved_links) == 5  # 2 existing + 3 new/retry
        link_urls = [link.link for link in saved_links]
        assert "https://example.com/existing1" in link_urls
        assert "https://example.com/existing2" in link_urls
        assert "https://example.com/new1" in link_urls
        assert "https://example.com/new2" in link_urls

    @pytest.mark.asyncio
    async def test_execute_with_unregistered_entity_group(self, link_collector, mock_get_link):
        """Test error handling when entity-group combination is not registered."""
        # Arrange
        entity_name = "unknown"
        group = "unknown"
        target_date = date(2025, 1, 15)

        # Act & Assert
        with pytest.raises(ValueError, match="No link collector registered for unknown:unknown"):
            await link_collector.execute(entity_name, group, target_date, commit=True)

    @pytest.mark.asyncio
    async def test_execute_with_empty_links(self, link_collector, mock_get_link):
        """Test link collection when get_link returns empty list."""
        # Arrange
        entity_name = "br_federal"
        group = "dou1"
        target_date = date(2025, 1, 15)
        mock_get_link.return_value = []

        # Act
        result = await link_collector.execute(entity_name, group, target_date, commit=True)

        # Assert
        assert result == []
        
        # Verify no links were saved to database
        saved_links = await link_collector.links_repo.get_links(entity_name, group, target_date)
        assert len(saved_links) == 0


class TestLinkCollectorRangeIntegration:
    """Integration tests for LinkCollectorRange usecase."""

    @pytest.mark.asyncio
    async def test_execute_success_weekdays_range(self, link_collector_range, mock_get_link):
        """Test successful range collection for weekdays."""
        # Arrange
        entity_name = "br_federal"
        group = "dou1"
        start_date = date(2025, 1, 13)  # Monday
        end_date = date(2025, 1, 17)    # Friday
        
        # Mock returns different links for each day
        mock_get_link.side_effect = [
            ["https://example.com/monday1", "https://example.com/monday2"],      # Monday
            ["https://example.com/tuesday1"],                                    # Tuesday
            ["https://example.com/wednesday1", "https://example.com/wednesday2", "https://example.com/wednesday3"],  # Wednesday
            ["https://example.com/thursday1"],                                   # Thursday
            ["https://example.com/friday1", "https://example.com/friday2"]       # Friday
        ]

        # Act
        result = await link_collector_range.execute(entity_name, group, start_date, end_date, commit=True)

        # Assert
        # Should have 5 weekdays (Monday to Friday)
        assert len(result) == 5
        
        # Verify each day's results
        monday = date(2025, 1, 13)
        tuesday = date(2025, 1, 14)
        wednesday = date(2025, 1, 15)
        thursday = date(2025, 1, 16)
        friday = date(2025, 1, 17)
        
        assert result[monday] == ["https://example.com/monday1", "https://example.com/monday2"]
        assert result[tuesday] == ["https://example.com/tuesday1"]
        assert result[wednesday] == ["https://example.com/wednesday1", "https://example.com/wednesday2", "https://example.com/wednesday3"]
        assert result[thursday] == ["https://example.com/thursday1"]
        assert result[friday] == ["https://example.com/friday1", "https://example.com/friday2"]

        # Verify mock was called 5 times (once for each weekday)
        assert mock_get_link.call_count == 5

        # Verify links were saved to database for each day
        for target_date, expected_links in result.items():
            saved_links = await link_collector_range.link_collector.links_repo.get_links(entity_name, group, target_date)
            assert len(saved_links) == len(expected_links)
            assert [link.link for link in saved_links] == expected_links

    @pytest.mark.asyncio
    async def test_execute_with_weekend_dates(self, link_collector_range, mock_get_link):
        """Test range collection that includes weekend dates (should be skipped)."""
        # Arrange
        entity_name = "br_federal"
        group = "dou1"
        start_date = date(2025, 1, 11)  # Saturday
        end_date = date(2025, 1, 13)    # Monday
        
        # Mock should only be called for Monday (weekday)
        mock_get_link.return_value = ["https://example.com/monday1"]

        # Act
        result = await link_collector_range.execute(entity_name, group, start_date, end_date, commit=True)

        # Assert
        # Should only have 1 weekday (Monday)
        assert len(result) == 1
        monday = date(2025, 1, 13)
        assert monday in result
        assert result[monday] == ["https://example.com/monday1"]
        
        # Mock should be called only once (for Monday)
        assert mock_get_link.call_count == 1

    @pytest.mark.asyncio
    async def test_execute_with_link_collector_error(self, link_collector_range, mock_get_link):
        """Test error handling when LinkCollector raises ValueError."""
        # Arrange
        entity_name = "unknown"
        group = "unknown"
        start_date = date(2025, 1, 13)  # Monday
        end_date = date(2025, 1, 13)    # Monday (single day)

        # Act & Assert
        with pytest.raises(ValueError, match="No link collector registered for unknown:unknown"):
            await link_collector_range.execute(entity_name, group, start_date, end_date, commit=True)

    @pytest.mark.asyncio
    async def test_execute_with_partial_failures(self, link_collector_range, mock_get_link):
        """Test range collection with some days failing."""
        # Arrange
        entity_name = "br_federal" 
        group = "dou1"
        start_date = date(2025, 1, 13)  # Monday
        end_date = date(2025, 1, 15)    # Wednesday
        
        # Mock fails on Tuesday, succeeds on Monday and Wednesday
        mock_get_link.side_effect = [
            ["https://example.com/monday1"],      # Monday - success
            Exception("Network error"),          # Tuesday - failure
            ["https://example.com/wednesday1"]   # Wednesday - success
        ]

        # Act
        result = await link_collector_range.execute(entity_name, group, start_date, end_date, commit=True)

        # Assert
        assert len(result) == 3
        monday = date(2025, 1, 13)
        tuesday = date(2025, 1, 14)
        wednesday = date(2025, 1, 15)
        
        assert result[monday] == ["https://example.com/monday1"]
        assert result[tuesday] == []  # Empty list for failed day
        assert result[wednesday] == ["https://example.com/wednesday1"]
        
        # Mock should be called 3 times
        assert mock_get_link.call_count == 3