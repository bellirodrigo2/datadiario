import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Callable

from dependency_injector import providers
from dotenv import load_dotenv
from src.app.usecase.getlinks import LinkCollector, LinkCollectorRange
from src.app.usecase.readlinks import LinkReader, LinkReaderRange
from src.infra.cli.cli_wrapper import ClickAdapter
from src.infra.controller.cli_controller import DouController
from src.infra.controller.mcp_controller import McpController
from src.infra.di.container import Container
from src.infra.gateway.linksgateway.br import (
    get_br_dou1_links,
    get_br_dou2_links,
    get_br_dou3_links,
)
from src.infra.mcp.mcp_wrapper import McpWrapper
from src.infra.repo.links_repo.db import make_session
from src.infra.repo.links_repo.model import Base
from src.infra.repo.links_repo.repo import LinksRepo

envfile = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=envfile)


def set_config_from_env(config: providers.Configuration) -> None:
    """Set configuration values from environment variables"""

    config.from_dict(
        {
            "database": {"url": "sqlite+aiosqlite:///:memory:"},
            "logging": {"level": "INFO"},
        }
    )

    # Priority: DATABASE_URL > DB_SELECTOR > default
    if "DATABASE_URL" in os.environ:
        # Direct database URL override (highest priority)
        config.database.url.from_env("DATABASE_URL")
    elif "DB_SELECTOR" in os.environ:
        # Database selector - use DB_SELECTOR to pick from predefined options
        selector = os.environ["DB_SELECTOR"]
        # Try to find corresponding DB_URL_{SELECTOR} environment variable
        env_var = f"DB_URL_{selector.upper()}"
        if env_var in os.environ:
            config.database.url.override(os.environ[env_var])
        else:
            # If no matching env var, treat selector as direct URL
            config.database.url.override(selector)

    # Logging level override
    if "LOG_LEVEL" in os.environ:
        config.logging.level.from_env("LOG_LEVEL")


def create_getlink_registry():

    return providers.Dict(
        br_federaldou1=providers.Object(get_br_dou1_links),
        br_federaldou2=providers.Object(get_br_dou2_links),
        br_federaldou3=providers.Object(get_br_dou3_links),
    )


async def create_container():
    """Create and configure the dependency injection container with all controllers."""
    container = Container()

    # Configuration provider with environment variables
    config = providers.Configuration()
    set_config_from_env(config)

    # Configure logging
    log_level = config.logging.level()
    logging.basicConfig(level=getattr(logging, log_level.upper()))
    logger = logging.getLogger("dou")

    # Create database session using config
    db_url = config.database.url()
    session_factory = await make_session(db_url, Base)

    @asynccontextmanager
    async def get_session():
        session = session_factory()
        try:
            yield session
        finally:
            await session.close()

    # Provide all dependencies
    container.provide("config", config)
    container.provide("logger", providers.Object(logger))
    container.provide("session_factory", providers.Object(session_factory))
    session = providers.Resource(get_session)
    links_repo = providers.Factory(LinksRepo, session=session)
    container.provide("links_repo", links_repo)

    # Create link registry - use the concrete implementation
    # container.provide("link_registry", providers.Object(get_link_registry))
    link_registry = create_getlink_registry()
    container.provide("link_registry", link_registry)

    # Create usecases
    container.provide(
        "link_collector",
        providers.Factory(
            LinkCollector,
            registry=container._container.link_registry,
            links_repo=container._container.links_repo,
            logger=container._container.logger,
        ),
    )

    container.provide(
        "link_collector_range",
        providers.Factory(
            LinkCollectorRange,
            link_collector=container._container.link_collector,
            logger=container._container.logger,
        ),
    )

    container.provide(
        "link_reader",
        providers.Factory(
            LinkReader,
            links_repo=container._container.links_repo,
            logger=container._container.logger,
        ),
    )

    container.provide(
        "link_reader_range",
        providers.Factory(
            LinkReaderRange,
            link_reader=container._container.link_reader,
            logger=container._container.logger,
        ),
    )

    return container


def cli() -> Any:
    """Main entry point for the DOU CLI application"""
    import asyncio

    async def async_cli():
        try:
            # Create container with all dependencies
            container = await create_container()

            container.provide("wrapper", providers.Object(ClickAdapter()))

            cli_controller = DouController(container)

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

        container.provide("wrapper", providers.Object(McpWrapper))

        # Create MCP controller manually
        mcp_controller = McpController(container=container)

        # Start the Controller
        return mcp_controller.start()

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
    async_run(mcp)
