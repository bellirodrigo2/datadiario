import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from src.app.usecase.getlinks import LinkCollector, LinkCollectorRange
from src.app.usecase.readlinks import LinkReader, LinkReaderRange
from src.infra.cli.cli_wrapper import ClickAdapter
from src.infra.controller.cli_controller import DouController
from src.infra.controller.mcp_controller import McpController
from src.infra.gateway.linksgateway.br import (
    get_br_dou1_links,
    get_br_dou2_links,
    get_br_dou3_links,
)
from src.infra.mcp.mcp_wrapper import FastMCPAdapter
from src.infra.repo.links_repo.db import make_session
from src.infra.repo.links_repo.model import Base
from src.infra.repo.links_repo.repo import LinksRepo


def load_env(envfile: Path):
    load_dotenv(dotenv_path=envfile)


def create_getlink_registry() -> dict[str, Callable[..., Any]]:
    return {
        "BR:DOU1": get_br_dou1_links,
        "BR:DOU2": get_br_dou2_links,
        "BR:DOU3": get_br_dou3_links,
    }


async def create_container() -> dict[str, Any]:

    envfile = Path(__file__).parent.parent / ".env"
    load_env(envfile)
    container: dict[str, Any] = {}

    log_level = os.environ.get("LOG_LEVEL", "INFO")
    logging.basicConfig(level=getattr(logging, log_level.upper()))
    logger = logging.getLogger("dou")
    container["logger"] = logger

    def get_database_url():
        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            return db_url

        db_selector = os.environ.get("DB_SELECTOR", "DB_URL_MEMORY")
        db_url = os.environ.get(db_selector)
        if not db_url:
            raise ValueError(
                f"Database URL not found. Please set DATABASE_URL or a valid DB_SELECTOR. Tried '{db_selector}'"
            )
        return db_url

    db_url = get_database_url()
    session_factory = await make_session(db_url, Base)
    container["session_factory"] = session_factory

    links_repo = LinksRepo(session_factory)
    container["links_repo"] = links_repo

    # Create link registry - use the concrete implementation
    # container.provide("link_registry", providers.Object(get_link_registry))
    link_registry = create_getlink_registry()
    container["links_registry"] = link_registry

    link_collector = LinkCollector(
        registry=link_registry, links_repo=links_repo, logger=logger
    )
    container["link_collector"] = link_collector

    link_collector_range = LinkCollectorRange(
        link_collector=link_collector, logger=logger
    )
    container["link_collector_range"] = link_collector_range

    link_reader = LinkReader(links_repo=links_repo, logger=logger)
    container["link_reader"] = link_reader

    link_reader_range = LinkReaderRange(link_reader=link_reader, logger=logger)
    container["link_reader_range"] = link_reader_range

    return container


def cli() -> Any:
    """Main entry point for the DOU CLI application"""
    import asyncio

    async def async_cli():
        try:
            # Create container with all dependencies
            container = await create_container()

            cli_adapter = ClickAdapter()

            cli_controller = DouController(cli=cli_adapter, **container)

            # Start the Controller
            return cli_controller.start()

        except Exception as e:
            logging.error(f"Failed to start DOU CLI: {e}")
            return 1

    return asyncio.run(async_cli())


async def mcp() -> Any:
    """Main entry point for the DOU MCP application"""
    try:
        # Create container with all dependencies
        container = await create_container()

        mcp_adapter = FastMCPAdapter()

        # Create MCP controller manually
        mcp_controller = McpController(mcp=mcp_adapter, **container)

        # Start the Controller (async version)
        return await mcp_controller.start_async()

    except Exception as e:
        logging.error(f"Failed to start DOU MCP Server: {e}")
        return 1


def async_run(afunc: Callable[..., Any]):
    import asyncio

    exit_code = asyncio.run(afunc())
    sys.exit(exit_code)


def run_cli():
    """Entry point for the CLI"""
    exit_code = cli()
    sys.exit(exit_code)


def run_mcp():
    """Entry point for the MCP server"""
    import asyncio

    exit_code = asyncio.run(mcp())
    sys.exit(exit_code)
