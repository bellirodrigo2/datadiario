import logging
import sys
from typing import Any

from dependency_injector import providers
from dou.infra.cli.cli_wrapper import CLIWrapper
from dou.infra.controller.cli_controller import DouController
from dou.infra.di.container_factory import create_container


async def main() -> Any:
    """Main entry point for the DOU CLI application"""
    try:
        # Create container with all dependencies
        container = await create_container()

        container.provide("wrapper", providers.Object(CLIWrapper))

        cli_controller = DouController(container)

        # Start the Controller
        return cli_controller.start()

    except Exception as e:
        logging.error(f"Failed to start DOU CLI: {e}")
        return 1


def run_main():
    """Entry point for the CLI"""
    import asyncio

    exit_code = asyncio.run(main())
    sys.exit(exit_code)


if __name__ == "__main__":
    run_main()
