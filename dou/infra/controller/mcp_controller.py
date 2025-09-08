"""MCP Controller that integrates FastMCP with usecases"""

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from dou.domain.entity.Link import LinkStatus
from dou.infra.controller.controller import IController
from infra.di.container import Container


class McpController(IController):
    """Controller that integrates MCP wrapper with domain usecases"""

    def __init__(
        self,
        container: Container,
    ):
        """
        Initialize McpController with MCP wrapper and usecases

        Args:
            container: Dependency injection container
        """
        self.mcp = container.inject("wrapper")
        self.link_collector = container.inject("link_collector")
        self.link_collector_range = container.inject("link_collector_range")
        self.link_reader = container.inject("link_reader")
        self.logger = container.inject("logger") or logging.getLogger(__name__)

        # Register all usecase tools and resources with FastMCP
        self._register_with_fastmcp()

    def _register_with_fastmcp(self):
        """Register all usecase functionality with FastMCP using decorators"""
        self.logger.info("Registering usecase tools and resources with FastMCP...")

        mcp_server = self.mcp.get_server()

        # Register collect-links tool
        @mcp_server.tool()
        async def collect_links(
            entity: str, group: str, date_str: str, commit: bool = True
        ) -> Dict[str, Any]:
            """
            Collect links for a specific entity/group/date

            Args:
                entity: Entity name (e.g., BR, US)
                group: Group name (e.g., DOU1, GOV)
                date_str: Date in YYYY-MM-DD format
                commit: Whether to save links to database
            """
            return await self._collect_links_impl(entity, group, date_str, commit)

        # Register collect-links-range tool
        @mcp_server.tool()
        async def collect_links_range(
            entity: str, group: str, start_date: str, end_date: str, commit: bool = True
        ) -> Dict[str, Any]:
            """
            Collect links for a date range

            Args:
                entity: Entity name
                group: Group name
                start_date: Start date (YYYY-MM-DD)
                end_date: End date (YYYY-MM-DD)
                commit: Whether to save links
            """
            return await self._collect_links_range_impl(
                entity, group, start_date, end_date, commit
            )

        # Register read-links tool
        @mcp_server.tool()
        async def read_links(
            entity: str, group: str, date_str: str, status: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Read and filter links from database

            Args:
                entity: Entity name
                group: Group name
                date_str: Date (YYYY-MM-DD)
                status: Filter by link status (pending, processed, failed)
            """
            return await self._read_links_impl(entity, group, date_str, status)

        # Register links database resource
        @mcp_server.resource("links://database")
        async def links_database() -> Dict[str, Any]:
            """Access to the links database for browsing stored links"""
            return await self._links_database_resource()

        # Register tools list resource
        @mcp_server.resource("tools://list")
        async def tools_list() -> Dict[str, Any]:
            """List of all available DOU data collection tools"""
            return await self._tools_list_resource()

        self.logger.info("All usecase tools and resources registered successfully")

    def _register_tools(self):
        """Register all usecase tools with the MCP wrapper"""
        self.logger.info("Registering usecase tools with MCP...")

        # Register collect-links tool
        self.mcp.add_tool(
            name="collect_links",
            handler=self._collect_links_tool,
            description="Collect links for a specific entity/group/date",
            input_schema={
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "description": "Entity name (e.g., BR, US)",
                    },
                    "group": {
                        "type": "string",
                        "description": "Group name (e.g., DOU1, GOV)",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format",
                    },
                    "commit": {
                        "type": "boolean",
                        "description": "Whether to save links to database",
                        "default": True,
                    },
                },
                "required": ["entity", "group", "date"],
            },
        )

        # Register collect-links-range tool
        self.mcp.add_tool(
            name="collect_links_range",
            handler=self._collect_links_range_tool,
            description="Collect links for a date range",
            input_schema={
                "type": "object",
                "properties": {
                    "entity": {"type": "string", "description": "Entity name"},
                    "group": {"type": "string", "description": "Group name"},
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)",
                    },
                    "commit": {
                        "type": "boolean",
                        "description": "Whether to save links",
                        "default": True,
                    },
                },
                "required": ["entity", "group", "start_date", "end_date"],
            },
        )

        # Register read-links tool
        self.mcp.add_tool(
            name="read_links",
            handler=self._read_links_tool,
            description="Read and filter links from database",
            input_schema={
                "type": "object",
                "properties": {
                    "entity": {"type": "string", "description": "Entity name"},
                    "group": {"type": "string", "description": "Group name"},
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "processed", "failed"],
                        "description": "Filter by link status",
                    },
                },
                "required": ["entity", "group", "date"],
            },
        )

        self.logger.info("All usecase tools registered successfully")

    def _register_resources(self):
        """Register all usecase resources with the MCP wrapper"""
        self.logger.info("Registering usecase resources with MCP...")

        # Register links database resource
        self.mcp.add_resource(
            uri="links://database",
            name="Links Database",
            handler=self._links_database_resource,
            description="Access to the links database for browsing stored links",
        )

        # Register tools list resource
        self.mcp.add_resource(
            uri="tools://list",
            name="Available Tools",
            handler=self._tools_list_resource,
            description="List of all available DOU data collection tools",
        )

        self.logger.info("All usecase resources registered successfully")

    async def _collect_links_impl(
        self, entity: str, group: str, date_str: str, commit: bool = True
    ) -> Dict[str, Any]:
        """Implementation of collect-links MCP tool"""
        try:
            # Parse date
            target_date = date.fromisoformat(date_str)

            # Execute usecase
            self.logger.info(f"Collecting links for {entity}:{group} on {target_date}")
            links = await self.link_collector.execute(
                entity, group, target_date, commit
            )

            return {
                "success": True,
                "entity": entity,
                "group": group,
                "date": date,
                "links_count": len(links),
                "links": links,
                "committed": commit,
            }

        except Exception as e:
            self.logger.error(f"Error collecting links: {e}")
            return {
                "success": False,
                "error": str(e),
                "entity": entity,
                "group": group,
                "date": date,
            }

    async def _collect_links_range_impl(
        self,
        entity: str,
        group: str,
        start_date: str,
        end_date: str,
        commit: bool = True,
    ) -> Dict[str, Any]:
        """Implementation of collect-links-range MCP tool"""
        try:
            # Parse dates
            start_date_obj = date.fromisoformat(start_date)
            end_date_obj = date.fromisoformat(end_date)

            # Execute usecase
            self.logger.info(
                f"Collecting links for {entity}:{group} from {start_date_obj} to {end_date_obj}"
            )
            results = await self.link_collector_range.execute(
                entity, group, start_date_obj, end_date_obj, commit
            )

            # Calculate totals
            total_links = sum(len(links) for links in results.values())

            return {
                "success": True,
                "entity": entity,
                "group": group,
                "start_date": start_date,
                "end_date": end_date,
                "total_links": total_links,
                "days_processed": len(results),
                "results": {
                    str(date_key): links for date_key, links in results.items()
                },
                "committed": commit,
            }

        except Exception as e:
            self.logger.error(f"Error collecting links range: {e}")
            return {
                "success": False,
                "error": str(e),
                "entity": entity,
                "group": group,
                "start_date": start_date,
                "end_date": end_date,
            }

    async def _read_links_impl(
        self, entity: str, group: str, date: str, status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Implementation of read-links MCP tool"""
        try:
            # Parse date
            target_date = date.fromisoformat(date)

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

            return {
                "success": True,
                "entity": entity,
                "group": group,
                "date": date,
                "status_filter": status,
                "links_count": len(links),
                "links": [
                    {"url": link.link, "status": link.status.value} for link in links
                ],
            }

        except Exception as e:
            self.logger.error(f"Error reading links: {e}")
            return {
                "success": False,
                "error": str(e),
                "entity": entity,
                "group": group,
                "date": date,
            }

    async def _links_database_resource(self) -> Dict[str, Any]:
        """Implementation of links database resource"""
        try:
            # Return summary information about the database
            return {
                "type": "database",
                "name": "DOU Links Database",
                "description": "Database containing collected DOU publication links",
                "tables": [
                    {
                        "name": "links",
                        "description": "Main links table with URLs and metadata",
                    }
                ],
                "usage": "Use read_links tool to query specific links by entity/group/date",
            }
        except Exception as e:
            self.logger.error(f"Error accessing links database resource: {e}")
            return {"error": str(e)}

    async def _tools_list_resource(self) -> Dict[str, Any]:
        """Implementation of tools list resource"""
        try:
            return {
                "available_tools": [
                    {
                        "name": "collect_links",
                        "description": "Collect links for a specific entity/group/date",
                        "parameters": ["entity", "group", "date", "commit"],
                    },
                    {
                        "name": "collect_links_range",
                        "description": "Collect links for a date range",
                        "parameters": [
                            "entity",
                            "group",
                            "start_date",
                            "end_date",
                            "commit",
                        ],
                    },
                    {
                        "name": "read_links",
                        "description": "Read and filter links from database",
                        "parameters": ["entity", "group", "date", "status"],
                    },
                ],
                "entities": ["br_federal"],
                "groups": ["dou1", "dou2", "dou3"],
            }
        except Exception as e:
            self.logger.error(f"Error accessing tools list resource: {e}")
            return {"error": str(e)}

    def start(self, args: Optional[List[str]] = None):
        """Start the MCP server and listen for requests"""
        self.logger.info("Starting DOU MCP Server...")

        # Parse arguments for TCP vs stdio mode
        host = None
        port = None

        if args:
            if "--tcp" in args:
                host = "localhost"
                port = 8080

                # Look for custom host/port
                if "--host" in args:
                    host_idx = args.index("--host") + 1
                    if host_idx < len(args):
                        host = args[host_idx]

                if "--port" in args:
                    port_idx = args.index("--port") + 1
                    if port_idx < len(args):
                        try:
                            port = int(args[port_idx])
                        except ValueError:
                            self.logger.warning(
                                f"Invalid port number, using default 8080"
                            )
                            port = 8080

        return self.mcp.serve(host=host, port=port)

    def get_registered_commands(self) -> List[str]:
        """Get list of all registered MCP tools and resources"""
        tools = self.mcp.list_tools()
        resources = self.mcp.list_resources()
        return tools + resources
