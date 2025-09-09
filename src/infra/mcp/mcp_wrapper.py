"""MCP wrapper using the official MCP Python SDK."""

import logging
from typing import Any, List, Optional

from mcp.server.fastmcp import FastMCP


class McpWrapper:

    server: Any

    def list_tools(self) -> List[str]: ...
    def list_resources(self) -> List[str]: ...
    def serve(self, host: Optional[str] = None, port: Optional[int] = None) -> int: ...


class FastMCPAdapter(McpWrapper):
    """A wrapper around the official MCP FastMCP server."""

    def __init__(
        self,
        name: str = "dou-mcp",
        description: str = "DOU Data Collection MCP Server",
        logger: Optional[logging.Logger] = None,
    ):
        self.name = name
        self.description = description
        self.mcp_server = FastMCP(name)
        self.logger = logger or logging.getLogger(__name__)
        self.logger.info(f"Initialized MCP server: {name}")

    @property
    def server(self) -> FastMCP:
        """Get the underlying FastMCP server instance."""
        return self.mcp_server

    def list_tools(self) -> List[str]:
        """Get list of registered tool names."""
        # FastMCP manages tools internally, this is a helper method
        return []  # Could be enhanced to track registered tools

    def list_resources(self) -> List[str]:
        """Get list of registered resource URIs."""
        # FastMCP manages resources internally, this is a helper method
        return []  # Could be enhanced to track registered resources

    async def serve_async(self) -> int:
        """
        Start the MCP server using stdio transport (async version).

        Returns:
            Exit code
        """
        try:
            self.logger.info(f"Starting MCP server '{self.name}' on stdio...")
            
            # Use FastMCP's async stdio transport
            await self.mcp_server.run_stdio_async()
            return 0

        except KeyboardInterrupt:
            self.logger.info("MCP server stopped by user")
            return 0
        except Exception as e:
            self.logger.error(f"MCP server error: {e}")
            return 1

    def serve(self, host: Optional[str] = None, port: Optional[int] = None) -> int:
        """
        Start the MCP server using stdio transport (sync version).

        Args:
            host: Ignored (for compatibility)
            port: Ignored (for compatibility)

        Returns:
            Exit code
        """
        try:
            self.logger.info(f"Starting MCP server '{self.name}' on stdio...")
            
            # Use FastMCP's built-in stdio transport
            self.mcp_server.run()
            return 0

        except KeyboardInterrupt:
            self.logger.info("MCP server stopped by user")
            return 0
        except Exception as e:
            self.logger.error(f"MCP server error: {e}")
            return 1
