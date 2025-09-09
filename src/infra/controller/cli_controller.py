# DouController that integrates CLIWrapper with usecases
import logging
import stat
from typing import Any, List, Optional

import click
from src.app.usecase.getlinks import LinkCollector, LinkCollectorRange
from src.app.usecase.readlinks import LinkReader, LinkReaderRange
from src.domain.entity.Link import LinkStatus
from src.infra.cli.cli_wrapper import CLIWrapper
from src.infra.controller.controller import IController
from src.infra.controller.utils import parse_date


class DouController(IController):
    """Controller that integrates CLI wrapper with domain usecases"""

    def __init__(
        self,
        cli: CLIWrapper,
        link_collector: LinkCollector,
        link_collector_range: LinkCollectorRange,
        link_reader: LinkReader,
        link_reader_range: LinkReaderRange,
        logger: logging.Logger,
        **kwargs: Any,
    ):
        """
        Initialize DouController with CLI wrapper and usecases

        Args:
            cli (CLIWrapper): CLI wrapper instance
            link_collector (LinkCollector): Usecase for collecting links for single date
            link_collector_range (LinkCollectorRange): Usecase for collecting links over date range
            link_reader (LinkReader): Usecase for reading/filtering links
            logger (logging.Logger): Logger instance
            **kwargs: Additional arguments (ignored)
        """

        self.cli: CLIWrapper = cli
        self.link_collector = link_collector
        self.link_collector_range = link_collector_range
        self.link_reader = link_reader
        self.link_reader_range = link_reader_range
        self.logger = logger or logging.getLogger(__name__)

        # Register all usecase commands with the CLI
        self._register_commands()

    def _register_commands(self):
        """Register all usecase commands with the CLI wrapper"""
        self.logger.info("Registering usecase commands with CLI...")

        # Register unified collect-links command (handles both single date and range)
        collect_links_cmd = self._create_collect_links_command()
        self.cli.add_command(collect_links_cmd, "collect-links")

        # Register read-links command
        read_links_cmd = self._create_read_links_command()
        self.cli.add_command(read_links_cmd, "read-links")

        self.logger.info("All usecase commands registered successfully")

    def _create_collect_links_command(self):
        """Create unified collect-links CLI command that handles both single date and date range"""

        @click.command(
            help="Collect links for entity/group - single date or date range"
        )
        @click.option(
            "--entity", "-e", required=True, help="Entity name (e.g., br_federal)"
        )
        @click.option(
            "--group", "-g", required=True, help="Group name (e.g., dou1, dou2, dou3)"
        )
        @click.option(
            "--date", "-d", help="Single date (YYYY-MM-DD or DD/MM/YYYY format)"
        )
        @click.option(
            "--start-date",
            "-st",
            help="Start date for range (YYYY-MM-DD or DD/MM/YYYY format)",
        )
        @click.option(
            "--end-date",
            "-et",
            help="End date for range (YYYY-MM-DD or DD/MM/YYYY format)",
        )
        @click.option(
            "--commit/--no-commit",
            default=True,
            help="Whether to save links to database",
        )
        @click.option("--output", "-o", help="Output file path (default: stdout)")
        def collect_links_command(
            entity: str,
            group: str,
            date: Optional[str],
            start_date: Optional[str],
            end_date: Optional[str],
            commit: bool,
            output: Optional[str],
        ):
            """Collect links for entity/group - automatically detects single date vs date range"""
            import asyncio
            import threading

            def run_in_new_loop():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        self._unified_collect_links_command_impl(
                            entity, group, date, start_date, end_date, commit, output
                        )
                    )
                finally:
                    loop.close()

            # Run in a separate thread to avoid event loop conflicts
            thread = threading.Thread(target=run_in_new_loop)
            thread.start()
            thread.join()

        return collect_links_command

    async def _unified_collect_links_command_impl(
        self,
        entity: str,
        group: str,
        date: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str],
        commit: bool,
        output: Optional[str],
    ):
        """Unified implementation that handles both single date and date range collection"""
        try:
            # Validate input - either single date or both start/end dates
            if date and (start_date or end_date):
                click.echo(
                    "Error: Cannot specify both --date and --start-date/--end-date",
                    err=True,
                )
                raise click.Abort()

            if not date and not (start_date and end_date):
                click.echo(
                    "Error: Must specify either --date or both --start-date and --end-date",
                    err=True,
                )
                raise click.Abort()

            # Single date mode
            if date:
                target_date = parse_date(date)
                self.logger.info(
                    f"Collecting links for {entity}:{group} on {target_date}"
                )
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

            # Date range mode
            else:
                start_target_date = parse_date(start_date)
                end_target_date = parse_date(end_date)

                self.logger.info(
                    f"Collecting links for {entity}:{group} from {start_target_date} to {end_target_date}"
                )
                results = await self.link_collector_range.execute(
                    entity, group, start_target_date, end_target_date, commit
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
                    click.echo(
                        f"Collected {total_links} links across {len(results)} days:"
                    )
                    for date_key, links in results.items():
                        click.echo(f"  {date_key}: {len(links)} links")

        except Exception as e:
            self.logger.error(f"Error collecting links: {e}")
            click.echo(f"Error: {e}", err=True)
            raise click.Abort()

    async def _unified_read_links_command_impl(
        self,
        entity: str,
        group: str,
        date: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str],
        status: Optional[str],
        commit: Optional[bool],
        output: Optional[str],
    ):
        """Unified implementation that handles both single date and date range collection"""
        try:
            # Validate input - either single date or both start/end dates
            if date and (start_date or end_date):
                click.echo(
                    "Error: Cannot specify both --date and --start-date/--end-date",
                    err=True,
                )
                raise click.Abort()

            if not date and not (start_date and end_date):
                click.echo(
                    "Error: Must specify either --date or both --start-date and --end-date",
                    err=True,
                )
                raise click.Abort()

            # Single date mode
            if date:
                target_date = parse_date(date)
                self.logger.info(
                    f"Collecting links for {entity}:{group} on {target_date}"
                )
                links = await self.link_reader.execute(
                    entity, group, target_date, status
                )

                click.echo(f"Collected {len(links)} links:")
                for link in links:
                    click.echo(f"  {link}")

            # Date range mode
            else:
                tgt_start_date = parse_date(start_date)
                tgt_end_date = parse_date(end_date)

                self.logger.info(
                    f"Collecting links for {entity}:{group} from {tgt_start_date} to {tgt_end_date}"
                )
                results = await self.link_collector_range.execute(
                    entity, group, tgt_start_date, tgt_end_date, commit
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
                    click.echo(
                        f"Collected {total_links} links across {len(results)} days:"
                    )
                    for date_key, links in results.items():
                        click.echo(f"  {date_key}: {len(links)} links")

        except Exception as e:
            self.logger.error(f"Error collecting links: {e}")
            click.echo(f"Error: {e}", err=True)
            raise click.Abort()

    def _create_read_links_command(self):
        """Create read-links CLI command"""

        @click.command(help="Read and filter links from database")
        @click.option("--entity", "-e", required=True, help="Entity name")
        @click.option("--group", "-g", required=True, help="Group name")
        @click.option(
            "--date", "-d", help="Single date (YYYY-MM-DD or DD/MM/YYYY format)"
        )
        @click.option(
            "--start-date",
            "-st",
            help="Start date for range (YYYY-MM-DD or DD/MM/YYYY format)",
        )
        @click.option(
            "--end-date",
            "-et",
            help="End date for range (YYYY-MM-DD or DD/MM/YYYY format)",
        )
        @click.option(
            "--status",
            type=click.Choice(["pending", "processed", "failed"]),
            help="Filter by link status",
        )
        @click.option(
            "--commit/--no-commit",
            default=True,
            help="Whether to save links to database",
        )
        @click.option("--output", "-o", help="Output file path (default: stdout)")
        def read_links_command(
            entity: str,
            group: str,
            date: str,
            start_date: Optional[str],
            end_date: Optional[str],
            status: Optional[str],
            commit: Optional[bool],
            output: Optional[str],
        ):
            """Read and filter links from database"""
            import asyncio
            import threading

            def run_in_new_loop():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(
                        self._unified_read_links_command_impl(
                            entity=entity,
                            group=group,
                            date=date,
                            start_date=start_date,
                            end_date=end_date,
                            status=status,
                            commit=commit,
                            output=output,
                        )
                    )
                finally:
                    loop.close()

            # Run in a separate thread to avoid event loop conflicts
            thread = threading.Thread(target=run_in_new_loop)
            thread.start()
            thread.join()

        return read_links_command

    def start(self, **kwargs: Any) -> int:
        """Start the CLI and listen for commands"""

        self.logger.info("Starting DOU CLI...")
        self.cli.listen()
        return 0

    def get_registered_commands(self) -> List[str]:
        """Get list of all registered commands"""
        return self.cli.list_commands()
