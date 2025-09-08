# DouController that integrates CLIWrapper with usecases
import logging
from datetime import date
from typing import List, Optional

import click
from dou.domain.entity.Link import LinkStatus
from dou.infra.controller.controller import IController
from dou.infra.di.container import Container


class DouController(IController):
    """Controller that integrates CLI wrapper with domain usecases"""

    def __init__(
        self,
        container: Container,
    ):
        """
        Initialize DouController with CLI wrapper and usecases

        Args:
            container: Dependency injection container
        """

        self.cli = container.inject("wrapper")
        self.link_collector = container.inject("link_collector")
        self.link_collector_range = container.inject("link_collector_range")
        self.link_reader = container.inject("link_reader")
        self.logger = container.inject("logger") or logging.getLogger(__name__)

        # Register all usecase commands with the CLI
        self._register_commands()

    def _register_commands(self):
        """Register all usecase commands with the CLI wrapper"""
        self.logger.info("Registering usecase commands with CLI...")

        # Register collect-links command
        collect_links_cmd = self._create_collect_links_command()
        self.cli.add_command(collect_links_cmd, "collect-links")

        # Register collect-links-range command
        collect_range_cmd = self._create_collect_links_range_command()
        self.cli.add_command(collect_range_cmd, "collect-links-range")

        # Register read-links command
        read_links_cmd = self._create_read_links_command()
        self.cli.add_command(read_links_cmd, "read-links")

        self.logger.info("All usecase commands registered successfully")

    def _create_collect_links_command(self):
        """Create collect-links CLI command"""

        @click.command(help="Collect links for a specific entity/group/date")
        @click.option("--entity", required=True, help="Entity name (e.g., BR, US)")
        @click.option("--group", required=True, help="Group name (e.g., DOU1, GOV)")
        @click.option(
            "--date", "date_str", required=True, help="Date in YYYY-MM-DD format"
        )
        @click.option(
            "--commit/--no-commit",
            default=True,
            help="Whether to save links to database",
        )
        @click.option("--output", "-o", help="Output file path (default: stdout)")
        def collect_links_command(
            entity: str, group: str, date_str: str, commit: bool, output: Optional[str]
        ):
            """Collect links for a specific entity/group/date"""
            import asyncio

            asyncio.run(
                self._collect_links_command_impl(
                    entity, group, date_str, commit, output
                )
            )

        return collect_links_command

    async def _collect_links_command_impl(
        self,
        entity: str,
        group: str,
        date_str: str,
        commit: bool,
        output: Optional[str],
    ):
        """Implementation of collect-links command"""
        try:
            # Parse date
            target_date = date.fromisoformat(date_str)

            # Execute usecase
            self.logger.info(f"Collecting links for {entity}:{group} on {target_date}")
            links = await self.link_collector.execute(
                entity, group, target_date, commit
            )

            # Output results
            if output:
                with open(output, "w") as f:
                    for link in links:
                        f.write(f"{link}\n")
                click.echo(f"Wrote {len(links)} links to {output}")
            else:
                click.echo(f"Collected {len(links)} links:")
                for link in links:
                    click.echo(f"  {link}")

        except Exception as e:
            self.logger.error(f"Error collecting links: {e}")
            click.echo(f"Error: {e}", err=True)
            raise click.Abort()

    def _create_collect_links_range_command(self):
        """Create collect-links-range CLI command"""

        @click.command(help="Collect links for a date range")
        @click.option("--entity", required=True, help="Entity name")
        @click.option("--group", required=True, help="Group name")
        @click.option(
            "--start-date",
            "start_date_str",
            required=True,
            help="Start date (YYYY-MM-DD)",
        )
        @click.option(
            "--end-date", "end_date_str", required=True, help="End date (YYYY-MM-DD)"
        )
        @click.option(
            "--commit/--no-commit", default=True, help="Whether to save links"
        )
        @click.option("--output", "-o", help="Output file path")
        def collect_links_range_command(
            entity: str,
            group: str,
            start_date_str: str,
            end_date_str: str,
            commit: bool,
            output: Optional[str],
        ):
            """Collect links for a date range"""
            import asyncio

            asyncio.run(
                self._collect_links_range_command_impl(
                    entity, group, start_date_str, end_date_str, commit, output
                )
            )

        return collect_links_range_command

    async def _collect_links_range_command_impl(
        self,
        entity: str,
        group: str,
        start_date_str: str,
        end_date_str: str,
        commit: bool,
        output: Optional[str],
    ):
        """Implementation of collect-links-range command"""
        try:
            # Parse dates
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)

            # Execute usecase
            self.logger.info(
                f"Collecting links for {entity}:{group} from {start_date} to {end_date}"
            )
            results = await self.link_collector_range.execute(
                entity, group, start_date, end_date, commit
            )

            # Calculate totals
            total_links = sum(len(links) for links in results.values())

            # Output results
            if output:
                with open(output, "w") as f:
                    for date_key, links in results.items():
                        f.write(f"# {date_key}\n")
                        for link in links:
                            f.write(f"{link}\n")
                        f.write("\n")
                click.echo(
                    f"Wrote {total_links} links across {len(results)} days to {output}"
                )
            else:
                click.echo(f"Collected {total_links} links across {len(results)} days:")
                for date_key, links in results.items():
                    click.echo(f"  {date_key}: {len(links)} links")

        except Exception as e:
            self.logger.error(f"Error collecting links range: {e}")
            click.echo(f"Error: {e}", err=True)
            raise click.Abort()

    def _create_read_links_command(self):
        """Create read-links CLI command"""

        @click.command(help="Read and filter links from database")
        @click.option("--entity", required=True, help="Entity name")
        @click.option("--group", required=True, help="Group name")
        @click.option("--date", "date_str", required=True, help="Date (YYYY-MM-DD)")
        @click.option(
            "--status",
            type=click.Choice(["pending", "processed", "failed"]),
            help="Filter by link status",
        )
        @click.option("--output", "-o", help="Output file path")
        def read_links_command(
            entity: str,
            group: str,
            date_str: str,
            status: Optional[str],
            output: Optional[str],
        ):
            """Read and filter links from database"""
            import asyncio

            asyncio.run(
                self._read_links_command_impl(entity, group, date_str, status, output)
            )

        return read_links_command

    async def _read_links_command_impl(
        self,
        entity: str,
        group: str,
        date_str: str,
        status: Optional[str],
        output: Optional[str],
    ):
        """Implementation of read-links command"""
        try:
            # Parse date
            target_date = date.fromisoformat(date_str)

            # Parse status filter
            status_filter = None
            if status:
                status_map = {
                    "pending": LinkStatus.PENDING,
                    "processed": LinkStatus.PROCESSED,
                    "failed": LinkStatus.FAILED,
                }
                status_filter = status_map[status]

            # Execute usecase
            self.logger.info(f"Reading links for {entity}:{group} on {target_date}")
            links = await self.link_reader.execute(
                entity, group, target_date, status_filter
            )

            # Output results
            if output:
                with open(output, "w") as f:
                    for link in links:
                        f.write(f"{link.link}\t{link.status.value}\n")
                click.echo(f"Wrote {len(links)} links to {output}")
            else:
                click.echo(f"Found {len(links)} links:")
                for link in links:
                    click.echo(f"  {link.link} [{link.status.value}]")

        except Exception as e:
            self.logger.error(f"Error reading links: {e}")
            click.echo(f"Error: {e}", err=True)
            raise click.Abort()

    def start(self, args: Optional[List[str]] = None):
        """Start the CLI and listen for commands"""
        import sys

        self.logger.info("Starting DOU CLI...")
        # If no args provided, read from command line
        if args is None:
            args = sys.argv[1:]
        return self.cli.listen(args=args)

    def get_registered_commands(self) -> List[str]:
        """Get list of all registered commands"""
        return self.cli.list_commands()
