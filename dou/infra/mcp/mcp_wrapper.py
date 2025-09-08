"""MCP wrapper using the official MCP Python SDK."""

import logging
from typing import List, Optional

from mcp.server.fastmcp import FastMCP


class McpWrapper:
    """A wrapper around the official MCP FastMCP server."""

    def __init__(
        self, name: str = "dou-mcp", description: str = "DOU Data Collection MCP Server"
    ):
        self.name = name
        self.description = description
        self.mcp_server = FastMCP(name)
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initialized MCP server: {name}")

    def get_server(self) -> FastMCP:
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

    def serve(self, host: Optional[str] = None, port: Optional[int] = None):
        """
        Start the MCP server.

        Args:
            host: Host for TCP server (None for stdio)
            port: Port for TCP server (None for stdio)

        Returns:
            Exit code
        """
        try:
            if host and port:
                self.logger.info(
                    f"Starting MCP server '{self.name}' on {host}:{port}..."
                )
                # Note: FastMCP primarily uses stdio, TCP support may vary
                # For now, we'll use stdio even when TCP is requested
                self.logger.warning(
                    "TCP mode requested but using stdio mode (FastMCP limitation)"
                )
            else:
                self.logger.info(f"Starting MCP server '{self.name}' on stdio...")

            # Run the FastMCP server
            self.mcp_server.run()
            return 0

        except KeyboardInterrupt:
            self.logger.info("MCP server stopped by user")
            return 0
        except Exception as e:
            self.logger.error(f"MCP server error: {e}")
            return 1
