"""MCP Controller that integrates FastMCP with usecases"""

import logging
from typing import Any, Dict, List, Optional

from src.app.usecase.getlinks import LinkCollector, LinkCollectorRange
from src.app.usecase.readlinks import LinkReader, LinkReaderRange
from src.domain.entity.Link import LinkStatus
from src.infra.controller.controller import IController
from src.infra.controller.utils import parse_date
from src.infra.mcp.mcp_wrapper import McpWrapper


class McpController(IController):
    """Controller that integrates MCP wrapper with domain usecases"""

    def __init__(
        self,
        mcp: McpWrapper,
        link_collector: LinkCollector,
        link_collector_range: LinkCollectorRange,
        link_reader: LinkReader,
        link_reader_range: LinkReaderRange,
        logger: Optional[logging.Logger] = None,
        **kwargs: Any,
    ):
        """
        Initialize McpController with MCP wrapper and usecases

        Args:
            container: Dependency injection container
        """
        self.mcp = mcp
        self.link_collector = link_collector
        self.link_collector_range = link_collector_range
        self.link_reader = link_reader
        self.link_reader_range = link_reader_range
        self.logger = logger or logging.getLogger(__name__)
        self._commands: list[str] = []

        self._register_tools()

    def _register_tools(self):
        """Register all usecase tools with the MCP wrapper"""
        self.logger.info("Registering usecase tools with MCP...")

        # Register collect-links tool (handles both single date and range)
        self.mcp.server.add_tool(
            self._collect_links_tool,
            name="collect_links",
            description="Collect links for entity/group - single date or date range",
        )
        self._commands.append("collect_links")

        # Register read-links tool
        self.mcp.server.add_tool(
            self._read_links_tool,
            name="read_links",
            description="Read and filter links from database",
        )
        self._commands.append("read_links")

        self.logger.info("All usecase tools registered successfully")

    async def _collect_links_tool(
        self,
        entity: str,
        group: str,
        date: str = None,
        start_date: str = None,
        end_date: str = None,
        commit: bool = True,
    ) -> Dict[str, Any]:
        """Collect links for entity/group - automatically detects single date vs date range"""
        try:
            # Validate input - either single date or both start/end dates
            if date and (start_date or end_date):
                return {
                    "success": False,
                    "error": "Cannot specify both date and start_date/end_date",
                }

            if not date and not (start_date and end_date):
                return {
                    "success": False,
                    "error": "Must specify either date or both start_date and end_date",
                }

            # Single date mode
            if date:
                target_date = parse_date(date)
                self.logger.info(
                    f"Collecting links for {entity}:{group} on {target_date}"
                )
                links = await self.link_collector.execute(
                    entity, group, target_date, commit
                )

                return {
                    "success": True,
                    "mode": "single_date",
                    "date": str(target_date),
                    "entity": entity,
                    "group": group,
                    "links_count": len(links),
                    "links": [str(link) for link in links],
                    "committed": commit,
                }

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

                return {
                    "success": True,
                    "mode": "date_range",
                    "start_date": str(start_target_date),
                    "end_date": str(end_target_date),
                    "entity": entity,
                    "group": group,
                    "total_links": total_links,
                    "days_processed": len(results),
                    "results": {
                        date_key: {
                            "links_count": len(links),
                            "links": [str(link) for link in links],
                        }
                        for date_key, links in results.items()
                    },
                    "committed": commit,
                }

        except Exception as e:
            self.logger.error(f"Error collecting links: {e}")
            return {"success": False, "error": str(e)}

    async def _read_links_tool(
        self,
        entity: str,
        group: str,
        date: str = None,
        start_date: str = None,
        end_date: str = None,
        status: str = None,
    ) -> Dict[str, Any]:
        """Read and filter links from database"""
        try:
            # Validate input - either single date or both start/end dates
            if date and (start_date or end_date):
                return {
                    "success": False,
                    "error": "Cannot specify both date and start_date/end_date",
                }

            if not date and not (start_date and end_date):
                return {
                    "success": False,
                    "error": "Must specify either date or both start_date and end_date",
                }

            # Parse status if provided
            link_status = None
            if status:
                status_map = {
                    "pending": LinkStatus.PENDING,
                    "processed": LinkStatus.PROCESSED,
                    "failed": LinkStatus.FAILED,
                }
                link_status = status_map.get(status.lower())
                if link_status is None:
                    return {
                        "success": False,
                        "error": f"Invalid status: {status}. Valid options: pending, processed, failed",
                    }

            # Single date mode
            if date:
                target_date = parse_date(date)
                self.logger.info(f"Reading links for {entity}:{group} on {target_date}")
                links = await self.link_reader.execute(
                    entity, group, target_date, link_status
                )

                return {
                    "success": True,
                    "mode": "single_date",
                    "date": str(target_date),
                    "entity": entity,
                    "group": group,
                    "status_filter": status,
                    "links_count": len(links),
                    "links": [str(link) for link in links],
                }

            # Date range mode
            else:
                start_target_date = parse_date(start_date)
                end_target_date = parse_date(end_date)

                self.logger.info(
                    f"Reading links for {entity}:{group} from {start_target_date} to {end_target_date}"
                )
                results = await self.link_reader_range.execute(
                    entity, group, start_target_date, end_target_date, link_status
                )

                # Calculate totals
                total_links = sum(len(links) for links in results.values())

                return {
                    "success": True,
                    "mode": "date_range",
                    "start_date": str(start_target_date),
                    "end_date": str(end_target_date),
                    "entity": entity,
                    "group": group,
                    "status_filter": status,
                    "total_links": total_links,
                    "days_processed": len(results),
                    "results": {
                        date_key: {
                            "links_count": len(links),
                            "links": [str(link) for link in links],
                        }
                        for date_key, links in results.items()
                    },
                }

        except Exception as e:
            self.logger.error(f"Error reading links: {e}")
            return {"success": False, "error": str(e)}

    async def start_async(self, **kwargs: Any) -> int:
        """Start the MCP server and listen for tool calls (async version)"""
        self.logger.info("Starting DOU MCP server...")
        return await self.mcp.serve_async()

    def start(self, **kwargs: Any) -> int:
        """Start the MCP server and listen for tool calls (sync version)"""
        self.logger.info("Starting DOU MCP server...")
        return self.mcp.serve()

    def get_registered_tools(self) -> List[str]:
        """Get list of all registered tools"""
        return self.mcp.list_tools()

    def get_registered_commands(self) -> list[str]:
        """Get list of all registered commands (tools in MCP context)"""
        return self._commands
