import pytest
import pytest_asyncio
from datetime import date
import logging

from src.app.usecase.readlinks import LinkReader, LinkReaderRange
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
def link_reader(links_repo, logger):
    """Create a LinkReader instance for testing."""
    return LinkReader(
        links_repo=links_repo,
        logger=logger
    )


@pytest.fixture
def link_reader_range(link_reader, logger):
    """Create a LinkReaderRange instance for testing."""
    return LinkReaderRange(
        link_reader=link_reader,
        logger=logger
    )


@pytest_asyncio.fixture
async def sample_links_data(links_repo):
    """Create sample links data in the database for testing."""
    entity_name = "br_federal"
    group = "dou1"
    target_date = date(2025, 1, 15)
    
    # Create links with different statuses
    links = [
        Link(link="https://example.com/pending1", status=LinkStatus.PENDING),
        Link(link="https://example.com/pending2", status=LinkStatus.PENDING),
        Link(link="https://example.com/processed1", status=LinkStatus.PROCESSED),
        Link(link="https://example.com/processed2", status=LinkStatus.PROCESSED),
        Link(link="https://example.com/failed1", status=LinkStatus.FAILED),
        Link(link="https://example.com/failed2", status=LinkStatus.FAILED)
    ]
    
    await links_repo.save_links(entity_name, group, target_date, links)
    return entity_name, group, target_date, links


class TestLinkReaderIntegration:
    """Integration tests for LinkReader usecase."""

    @pytest.mark.asyncio
    async def test_execute_success_all_links(self, link_reader, sample_links_data):
        """Test successful reading of all links without status filter."""
        # Arrange
        entity_name, group, target_date, expected_links = sample_links_data

        # Act
        result = await link_reader.execute(entity_name, group, target_date)

        # Assert
        assert len(result) == 6  # All links
        
        # Verify links are returned correctly
        result_urls = [link.link for link in result]
        expected_urls = [link.link for link in expected_links]
        
        for expected_url in expected_urls:
            assert expected_url in result_urls
            
        # Verify status distribution
        pending_count = sum(1 for link in result if link.status == LinkStatus.PENDING)
        processed_count = sum(1 for link in result if link.status == LinkStatus.PROCESSED)
        failed_count = sum(1 for link in result if link.status == LinkStatus.FAILED)
        
        assert pending_count == 2
        assert processed_count == 2
        assert failed_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_pending_filter(self, link_reader, sample_links_data):
        """Test reading links with PENDING status filter."""
        # Arrange
        entity_name, group, target_date, _ = sample_links_data

        # Act
        result = await link_reader.execute(entity_name, group, target_date, LinkStatus.PENDING)

        # Assert
        assert len(result) == 2  # Only pending links
        assert all(link.status == LinkStatus.PENDING for link in result)
        
        result_urls = [link.link for link in result]
        assert "https://example.com/pending1" in result_urls
        assert "https://example.com/pending2" in result_urls

    @pytest.mark.asyncio
    async def test_execute_with_processed_filter(self, link_reader, sample_links_data):
        """Test reading links with PROCESSED status filter."""
        # Arrange
        entity_name, group, target_date, _ = sample_links_data

        # Act
        result = await link_reader.execute(entity_name, group, target_date, LinkStatus.PROCESSED)

        # Assert
        assert len(result) == 2  # Only processed links
        assert all(link.status == LinkStatus.PROCESSED for link in result)
        
        result_urls = [link.link for link in result]
        assert "https://example.com/processed1" in result_urls
        assert "https://example.com/processed2" in result_urls

    @pytest.mark.asyncio
    async def test_execute_with_failed_filter(self, link_reader, sample_links_data):
        """Test reading links with FAILED status filter."""
        # Arrange
        entity_name, group, target_date, _ = sample_links_data

        # Act
        result = await link_reader.execute(entity_name, group, target_date, LinkStatus.FAILED)

        # Assert
        assert len(result) == 2  # Only failed links
        assert all(link.status == LinkStatus.FAILED for link in result)
        
        result_urls = [link.link for link in result]
        assert "https://example.com/failed1" in result_urls
        assert "https://example.com/failed2" in result_urls

    @pytest.mark.asyncio
    async def test_execute_empty_results(self, link_reader):
        """Test reading links when no links exist for the given parameters."""
        # Arrange
        entity_name = "br_federal"
        group = "dou1"
        target_date = date(2025, 1, 20)  # Date with no links

        # Act
        result = await link_reader.execute(entity_name, group, target_date)

        # Assert
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_execute_empty_results_with_filter(self, link_reader, sample_links_data):
        """Test reading links when no links match the status filter."""
        # Arrange
        entity_name, group, target_date, _ = sample_links_data
        
        # Create new entry with only PENDING links
        only_pending_links = [
            Link(link="https://example.com/only_pending1", status=LinkStatus.PENDING),
            Link(link="https://example.com/only_pending2", status=LinkStatus.PENDING)
        ]
        new_date = date(2025, 1, 16)
        await link_reader.links_repo.save_links(entity_name, group, new_date, only_pending_links)

        # Act - filter for PROCESSED links when none exist
        result = await link_reader.execute(entity_name, group, new_date, LinkStatus.PROCESSED)

        # Assert
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_execute_nonexistent_entity_group(self, link_reader):
        """Test reading links for non-existent entity/group combination."""
        # Arrange
        entity_name = "unknown"
        group = "unknown"
        target_date = date(2025, 1, 15)

        # Act
        result = await link_reader.execute(entity_name, group, target_date)

        # Assert
        assert len(result) == 0


class TestLinkReaderRangeIntegration:
    """Integration tests for LinkReaderRange usecase."""

    @pytest_asyncio.fixture
    async def range_sample_data(self, links_repo):
        """Create sample links data across multiple days for range testing."""
        entity_name = "br_federal"
        group = "dou1"
        
        # Monday - 2025-01-13
        monday = date(2025, 1, 13)
        monday_links = [
            Link(link="https://example.com/monday1", status=LinkStatus.PENDING),
            Link(link="https://example.com/monday2", status=LinkStatus.PROCESSED)
        ]
        await links_repo.save_links(entity_name, group, monday, monday_links)
        
        # Tuesday - 2025-01-14
        tuesday = date(2025, 1, 14)
        tuesday_links = [
            Link(link="https://example.com/tuesday1", status=LinkStatus.FAILED),
            Link(link="https://example.com/tuesday2", status=LinkStatus.PROCESSED),
            Link(link="https://example.com/tuesday3", status=LinkStatus.PENDING)
        ]
        await links_repo.save_links(entity_name, group, tuesday, tuesday_links)
        
        # Wednesday - 2025-01-15
        wednesday = date(2025, 1, 15)
        wednesday_links = [
            Link(link="https://example.com/wednesday1", status=LinkStatus.PROCESSED)
        ]
        await links_repo.save_links(entity_name, group, wednesday, wednesday_links)
        
        # Thursday - 2025-01-16 (no links)
        
        # Friday - 2025-01-17
        friday = date(2025, 1, 17)
        friday_links = [
            Link(link="https://example.com/friday1", status=LinkStatus.FAILED),
            Link(link="https://example.com/friday2", status=LinkStatus.FAILED)
        ]
        await links_repo.save_links(entity_name, group, friday, friday_links)
        
        return {
            "entity_name": entity_name,
            "group": group,
            "monday": (monday, monday_links),
            "tuesday": (tuesday, tuesday_links),
            "wednesday": (wednesday, wednesday_links),
            "friday": (friday, friday_links)
        }

    @pytest.mark.asyncio
    async def test_execute_success_full_week_range(self, link_reader_range, range_sample_data):
        """Test successful range reading for a full week."""
        # Arrange
        entity_name = range_sample_data["entity_name"]
        group = range_sample_data["group"]
        start_date = date(2025, 1, 13)  # Monday
        end_date = date(2025, 1, 17)    # Friday

        # Act
        result = await link_reader_range.execute(entity_name, group, start_date, end_date)

        # Assert
        # Should have 5 weekdays (Monday to Friday)
        assert len(result) == 5
        
        monday = date(2025, 1, 13)
        tuesday = date(2025, 1, 14)
        wednesday = date(2025, 1, 15)
        thursday = date(2025, 1, 16)
        friday = date(2025, 1, 17)
        
        # Verify each day's results
        assert len(result[monday]) == 2
        assert len(result[tuesday]) == 3
        assert len(result[wednesday]) == 1
        assert len(result[thursday]) == 0  # No links for Thursday
        assert len(result[friday]) == 2

    @pytest.mark.asyncio
    async def test_execute_with_status_filter(self, link_reader_range, range_sample_data):
        """Test range reading with status filter."""
        # Arrange
        entity_name = range_sample_data["entity_name"]
        group = range_sample_data["group"]
        start_date = date(2025, 1, 13)  # Monday
        end_date = date(2025, 1, 17)    # Friday

        # Act - filter for PROCESSED links only
        result = await link_reader_range.execute(entity_name, group, start_date, end_date, LinkStatus.PROCESSED)

        # Assert
        monday = date(2025, 1, 13)
        tuesday = date(2025, 1, 14)
        wednesday = date(2025, 1, 15)
        thursday = date(2025, 1, 16)
        friday = date(2025, 1, 17)
        
        assert len(result[monday]) == 1  # 1 PROCESSED
        assert len(result[tuesday]) == 1  # 1 PROCESSED
        assert len(result[wednesday]) == 1  # 1 PROCESSED
        assert len(result[thursday]) == 0  # No links
        assert len(result[friday]) == 0  # No PROCESSED links
        
        # Verify all returned links have PROCESSED status
        for day_links in result.values():
            assert all(link.status == LinkStatus.PROCESSED for link in day_links)

    @pytest.mark.asyncio
    async def test_execute_with_failed_filter(self, link_reader_range, range_sample_data):
        """Test range reading with FAILED status filter."""
        # Arrange
        entity_name = range_sample_data["entity_name"]
        group = range_sample_data["group"]
        start_date = date(2025, 1, 13)  # Monday
        end_date = date(2025, 1, 17)    # Friday

        # Act - filter for FAILED links only
        result = await link_reader_range.execute(entity_name, group, start_date, end_date, LinkStatus.FAILED)

        # Assert
        monday = date(2025, 1, 13)
        tuesday = date(2025, 1, 14)
        wednesday = date(2025, 1, 15)
        thursday = date(2025, 1, 16)
        friday = date(2025, 1, 17)
        
        assert len(result[monday]) == 0  # No FAILED links
        assert len(result[tuesday]) == 1  # 1 FAILED
        assert len(result[wednesday]) == 0  # No FAILED links
        assert len(result[thursday]) == 0  # No links
        assert len(result[friday]) == 2  # 2 FAILED
        
        # Verify all returned links have FAILED status
        for day_links in result.values():
            assert all(link.status == LinkStatus.FAILED for link in day_links)

    @pytest.mark.asyncio
    async def test_execute_single_day_range(self, link_reader_range, range_sample_data):
        """Test range reading for a single day."""
        # Arrange
        entity_name = range_sample_data["entity_name"]
        group = range_sample_data["group"]
        tuesday = date(2025, 1, 14)  # Tuesday only

        # Act
        result = await link_reader_range.execute(entity_name, group, tuesday, tuesday)

        # Assert
        assert len(result) == 1
        assert tuesday in result
        assert len(result[tuesday]) == 3  # Tuesday has 3 links

    @pytest.mark.asyncio
    async def test_execute_weekend_only_range(self, link_reader_range, range_sample_data):
        """Test range reading for weekend dates only (should return empty)."""
        # Arrange
        entity_name = range_sample_data["entity_name"]
        group = range_sample_data["group"]
        start_date = date(2025, 1, 18)  # Saturday
        end_date = date(2025, 1, 19)    # Sunday

        # Act
        result = await link_reader_range.execute(entity_name, group, start_date, end_date)

        # Assert
        assert len(result) == 0  # No weekdays in range

    @pytest.mark.asyncio
    async def test_execute_range_with_partial_data(self, link_reader_range, range_sample_data):
        """Test range reading where some days have data and others don't."""
        # Arrange
        entity_name = range_sample_data["entity_name"]
        group = range_sample_data["group"]
        start_date = date(2025, 1, 16)  # Thursday (no data)
        end_date = date(2025, 1, 17)    # Friday (has data)

        # Act
        result = await link_reader_range.execute(entity_name, group, start_date, end_date)

        # Assert
        thursday = date(2025, 1, 16)
        friday = date(2025, 1, 17)
        
        assert len(result) == 2
        assert len(result[thursday]) == 0  # No links for Thursday
        assert len(result[friday]) == 2   # Friday has links

    @pytest.mark.asyncio
    async def test_execute_nonexistent_entity_group_range(self, link_reader_range):
        """Test range reading for non-existent entity/group combination."""
        # Arrange
        entity_name = "unknown"
        group = "unknown"
        start_date = date(2025, 1, 13)
        end_date = date(2025, 1, 17)

        # Act
        result = await link_reader_range.execute(entity_name, group, start_date, end_date)

        # Assert
        # Should return entries for each weekday but with empty link lists
        assert len(result) == 5  # 5 weekdays
        for day_links in result.values():
            assert len(day_links) == 0