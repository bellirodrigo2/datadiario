import logging
import sys
from typing import Any

from dependency_injector import providers
from dou.infra.controller.mcp_controller import McpController
from dou.infra.di.container_factory import create_container
from dou.infra.mcp.mcp_wrapper import McpWrapper


async def main() -> Any:
    """Main entry point for the DOU MCP application"""
    try:
        # Create container with all dependencies
        container = await create_container()

        container.provide("wrapper", providers.Object(McpWrapper))

        # Create MCP controller manually
        mcp_controller = McpController(container=container)

        # Start the Controller
        return mcp_controller.start()

    except Exception as e:
        logging.error(f"Failed to start DOU MCP Server: {e}")
        return 1


def run_main():
    """Entry point for the MCP server"""
    import asyncio

    exit_code = asyncio.run(main())
    sys.exit(exit_code)


if __name__ == "__main__":
    run_main()
