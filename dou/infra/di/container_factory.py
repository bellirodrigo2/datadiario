"""Container factory for dependency injection."""

import logging
import os

from dependency_injector import providers
from dou.app.gateway.links import IGetLinkRegistry
from dou.app.usecase.getlinks import LinkCollector, LinkCollectorRange
from dou.app.usecase.readlinks import LinkReader, LinkReaderRange
from dou.infra.cli.cli_wrapper import CLIWrapper
from dou.infra.controller.cli_controller import DouController
from dou.infra.controller.mcp_controller import McpController
from dou.infra.di.container import Container
from dou.infra.gateway.linksgateway.register import get_link_registry
from dou.infra.mcp.mcp_wrapper import McpWrapper
from dou.infra.repo.links_repo.db import make_session
from dou.infra.repo.links_repo.model import Base
from dou.infra.repo.links_repo.repo import LinksRepo


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

    # Provide all dependencies
    container.provide("config", config)
    container.provide("logger", providers.Object(logger))
    container.provide("session_factory", providers.Object(session_factory))

    # Create link registry - use the concrete implementation
    container.provide("link_registry", providers.Object(get_link_registry))

    # Create repository with actual session
    async def create_repo():
        async with session_factory() as session:
            return LinksRepo(session)

    container.provide("links_repo", providers.Object(await create_repo()))

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
