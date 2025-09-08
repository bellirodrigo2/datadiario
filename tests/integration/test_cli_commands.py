import asyncio
import logging
from datetime import date
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner
from dou.infra.cli.cli_wrapper import CLIWrapper
from dou.infra.controller.cli_controller import DouController


class TestCLICommands:
    """Test suite for CLI command execution with mocked usecases"""

    @pytest.fixture
    def mock_logger(self):
        return Mock(spec=logging.Logger)

    @pytest.fixture
    def mock_link_collector(self):
        mock = AsyncMock()
        mock.execute.return_value = [
            "https://example1.com",
            "https://example2.com",
            "https://example3.com",
        ]
        return mock

    @pytest.fixture
    def mock_link_collector_range(self):
        mock = AsyncMock()
        mock.execute.return_value = {
            date(2023, 2, 13): ["https://monday1.com", "https://monday2.com"],
            date(2023, 2, 14): ["https://tuesday1.com"],
            date(2023, 2, 15): ["https://wednesday1.com", "https://wednesday2.com"],
        }
        return mock

    @pytest.fixture
    def mock_link_reader(self):
        from dou.domain.entity.Link import Link, LinkStatus

        mock = AsyncMock()
        mock.execute.return_value = [
            Link(link="https://pending1.com", status=LinkStatus.PENDING),
            Link(link="https://processed1.com", status=LinkStatus.PROCESSED),
            Link(link="https://failed1.com", status=LinkStatus.FAILED),
        ]
        return mock

    @pytest.fixture
    def mock_cli_wrapper(self):
        return CLIWrapper(name="test-cli", help_text="Test CLI")

    @pytest.fixture
    def controller(
        self,
        mock_cli_wrapper,
        mock_link_collector,
        mock_link_collector_range,
        mock_link_reader,
        mock_logger,
    ):
        """Create DouController with mocked dependencies"""
        return DouController(
            cli_wrapper=mock_cli_wrapper,
            link_collector=mock_link_collector,
            link_collector_range=mock_link_collector_range,
            link_reader=mock_link_reader,
            logger=mock_logger,
        )

    def test_collect_links_command_with_commit(self, controller, mock_link_collector):
        """Test collect-links command with commit"""
        runner = CliRunner()

        # Act
        result = runner.invoke(
            controller.cli.cli_group,
            [
                "collect-links",
                "--entity",
                "BR",
                "--group",
                "DOU1",
                "--date",
                "2023-02-15",
                "--commit",
            ],
        )

        # Assert
        assert result.exit_code == 0
        assert "Collected 3 links:" in result.output
        assert "https://example1.com" in result.output
        assert "https://example2.com" in result.output
        assert "https://example3.com" in result.output

        # Verify usecase was called correctly
        mock_link_collector.execute.assert_called_once_with(
            "BR", "DOU1", date(2023, 2, 15), True
        )

    def test_collect_links_command_no_commit(self, controller, mock_link_collector):
        """Test collect-links command without commit"""
        runner = CliRunner()

        # Act
        result = runner.invoke(
            controller.cli.cli_group,
            [
                "collect-links",
                "--entity",
                "US",
                "--group",
                "GOV",
                "--date",
                "2023-03-01",
                "--no-commit",
            ],
        )

        # Assert
        assert result.exit_code == 0
        assert "Collected 3 links:" in result.output

        # Verify usecase was called with commit=False
        mock_link_collector.execute.assert_called_once_with(
            "US", "GOV", date(2023, 3, 1), False
        )

    def test_collect_links_command_with_output_file(
        self, controller, mock_link_collector
    ):
        """Test collect-links command with output file"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Act
            result = runner.invoke(
                controller.cli.cli_group,
                [
                    "collect-links",
                    "--entity",
                    "BR",
                    "--group",
                    "DOU1",
                    "--date",
                    "2023-02-15",
                    "--commit",
                    "-o",
                    "links.txt",
                ],
            )

            # Assert
            assert result.exit_code == 0
            assert "Wrote 3 links to links.txt" in result.output

            # Verify file was created
            with open("links.txt", "r") as f:
                content = f.read()
                assert "https://example1.com" in content
                assert "https://example2.com" in content
                assert "https://example3.com" in content

    def test_collect_links_range_command(self, controller, mock_link_collector_range):
        """Test collect-links-range command"""
        runner = CliRunner()

        # Act
        result = runner.invoke(
            controller.cli.cli_group,
            [
                "collect-links-range",
                "--entity",
                "BR",
                "--group",
                "DOU1",
                "--start-date",
                "2023-02-13",
                "--end-date",
                "2023-02-15",
                "--commit",
            ],
        )

        # Assert
        assert result.exit_code == 0
        assert "Collected 5 links across 3 days:" in result.output
        assert "2023-02-13: 2 links" in result.output
        assert "2023-02-14: 1 links" in result.output
        assert "2023-02-15: 2 links" in result.output

        # Verify usecase was called correctly
        mock_link_collector_range.execute.assert_called_once_with(
            "BR", "DOU1", date(2023, 2, 13), date(2023, 2, 15), True
        )

    def test_collect_links_range_with_output_file(
        self, controller, mock_link_collector_range
    ):
        """Test collect-links-range command with output file"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Act
            result = runner.invoke(
                controller.cli.cli_group,
                [
                    "collect-links-range",
                    "--entity",
                    "BR",
                    "--group",
                    "DOU1",
                    "--start-date",
                    "2023-02-13",
                    "--end-date",
                    "2023-02-15",
                    "--commit",
                    "-o",
                    "range_links.txt",
                ],
            )

            # Assert
            assert result.exit_code == 0
            assert "Wrote 5 links across 3 days to range_links.txt" in result.output

            # Verify file content
            with open("range_links.txt", "r") as f:
                content = f.read()
                assert "# 2023-02-13" in content
                assert "https://monday1.com" in content
                assert "# 2023-02-14" in content
                assert "https://tuesday1.com" in content

    def test_read_links_command_no_filter(self, controller, mock_link_reader):
        """Test read-links command without status filter"""
        runner = CliRunner()

        # Act
        result = runner.invoke(
            controller.cli.cli_group,
            ["read-links", "--entity", "BR", "--group", "DOU1", "--date", "2023-02-15"],
        )

        # Assert
        assert result.exit_code == 0
        assert "Found 3 links:" in result.output
        assert "https://pending1.com [pending]" in result.output
        assert "https://processed1.com [processed]" in result.output
        assert "https://failed1.com [failed]" in result.output

        # Verify usecase was called correctly
        mock_link_reader.execute.assert_called_once_with(
            "BR", "DOU1", date(2023, 2, 15), None
        )

    def test_read_links_command_with_status_filter(self, controller, mock_link_reader):
        """Test read-links command with status filter"""
        from dou.domain.entity.Link import Link, LinkStatus

        # Mock filtered response
        mock_link_reader.execute.return_value = [
            Link(link="https://pending1.com", status=LinkStatus.PENDING),
            Link(link="https://pending2.com", status=LinkStatus.PENDING),
        ]

        runner = CliRunner()

        # Act
        result = runner.invoke(
            controller.cli.cli_group,
            [
                "read-links",
                "--entity",
                "BR",
                "--group",
                "DOU1",
                "--date",
                "2023-02-15",
                "--status",
                "pending",
            ],
        )

        # Assert
        assert result.exit_code == 0
        assert "Found 2 links:" in result.output
        assert "https://pending1.com [pending]" in result.output
        assert "https://pending2.com [pending]" in result.output

        # Verify usecase was called with status filter
        from dou.domain.entity.Link import LinkStatus

        mock_link_reader.execute.assert_called_once_with(
            "BR", "DOU1", date(2023, 2, 15), LinkStatus.PENDING
        )

    def test_read_links_command_with_output_file(self, controller, mock_link_reader):
        """Test read-links command with output file"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Act
            result = runner.invoke(
                controller.cli.cli_group,
                [
                    "read-links",
                    "--entity",
                    "BR",
                    "--group",
                    "DOU1",
                    "--date",
                    "2023-02-15",
                    "-o",
                    "read_links.txt",
                ],
            )

            # Assert
            assert result.exit_code == 0
            assert "Wrote 3 links to read_links.txt" in result.output

            # Verify file content
            with open("read_links.txt", "r") as f:
                content = f.read()
                assert "https://pending1.com\tpending" in content
                assert "https://processed1.com\tprocessed" in content
                assert "https://failed1.com\tfailed" in content

    def test_collect_links_command_invalid_date(self, controller, mock_link_collector):
        """Test collect-links command with invalid date format"""
        runner = CliRunner()

        # Act
        result = runner.invoke(
            controller.cli.cli_group,
            [
                "collect-links",
                "--entity",
                "BR",
                "--group",
                "DOU1",
                "--date",
                "invalid-date",
                "--commit",
            ],
        )

        # Assert
        assert result.exit_code != 0
        assert "Error:" in result.output

        # Verify usecase was not called
        mock_link_collector.execute.assert_not_called()

    def test_collect_links_range_invalid_date_range(
        self, controller, mock_link_collector_range
    ):
        """Test collect-links-range command with invalid date range"""
        runner = CliRunner()

        # Act
        result = runner.invoke(
            controller.cli.cli_group,
            [
                "collect-links-range",
                "--entity",
                "BR",
                "--group",
                "DOU1",
                "--start-date",
                "2023-02-15",
                "--end-date",
                "2023-02-13",
                "--commit",
            ],
        )

        # Assert - should still execute (the usecase should handle invalid ranges)
        assert result.exit_code == 0
        mock_link_collector_range.execute.assert_called_once()

    def test_usecase_exception_handling(
        self, controller, mock_link_collector, mock_logger
    ):
        """Test CLI handles usecase exceptions gracefully"""
        # Mock usecase to raise an exception
        mock_link_collector.execute.side_effect = Exception(
            "Database connection failed"
        )

        runner = CliRunner()

        # Act
        result = runner.invoke(
            controller.cli.cli_group,
            [
                "collect-links",
                "--entity",
                "BR",
                "--group",
                "DOU1",
                "--date",
                "2023-02-15",
                "--commit",
            ],
        )

        # Assert
        assert result.exit_code != 0
        assert "Error: Database connection failed" in result.output

        # Verify error was logged
        mock_logger.error.assert_called()

    def test_cli_help_command(self, controller):
        """Test CLI help command"""
        runner = CliRunner()

        # Act
        result = runner.invoke(controller.cli.cli_group, ["--help"])

        # Assert
        assert result.exit_code == 0
        assert "collect-links" in result.output
        assert "collect-links-range" in result.output
        assert "read-links" in result.output

    def test_collect_links_help(self, controller):
        """Test collect-links help"""
        runner = CliRunner()

        # Act
        result = runner.invoke(controller.cli.cli_group, ["collect-links", "--help"])

        # Assert
        assert result.exit_code == 0
        assert "--entity" in result.output
        assert "--group" in result.output
        assert "--date" in result.output
        assert "--commit" in result.output
        assert "--output" in result.output

    def test_missing_required_arguments(self, controller):
        """Test CLI with missing required arguments"""
        runner = CliRunner()

        # Act - missing required arguments
        result = runner.invoke(controller.cli.cli_group, ["collect-links"])

        # Assert
        assert result.exit_code != 0
        assert "Missing option" in result.output

    def test_all_commands_registered(self, controller):
        """Test that all expected commands are registered"""
        commands = controller.get_registered_commands()

        assert "collect-links" in commands
        assert "collect-links-range" in commands
        assert "read-links" in commands
        assert len(commands) == 3
