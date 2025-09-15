import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from dateutil import parser as date_parser
from dotenv import load_dotenv

from .app.usecase.insertcontent import ContentCollector
from .app.usecase.insertlinks import LinkCollector
from .app.usecase.readlinks import LinkReader
from .app.usecase.retrylinks import LinkRetry
from .app.usecase.usecase import UseCase
from .infra.db.sqlite_adapter import SQLiteAdapter
from .infra.gateway.contentgateway.br import parse_br_content
from .infra.gateway.linksgateway.br import (
    get_br_dou1_links,
    get_br_dou2_links,
    get_br_dou3_links,
)
from .infra.gateway.linksgateway.ce import get_ceara_links
from .infra.repo.file_content_repo import FileContentRepoAdapter
from .infra.repo.sql_repo import SQLLinksRepo
from .infra.web.httpreq import AsyncHttpx


def create_getlink_registry() -> dict[str, Callable[..., Any]]:
    return {
        "BR:DOU1": get_br_dou1_links,
        "BR:DOU2": get_br_dou2_links,
        "BR:DOU3": get_br_dou3_links,
        "CE:DOU": get_ceara_links,
    }


def create_getcontent_registry() -> dict[str, Callable[..., Any]]:
    return {
        "BR:DOU1": parse_br_content,
        "BR:DOU2": parse_br_content,
        "BR:DOU3": parse_br_content,
    }


def init():
    load_dotenv()


def get_logger():
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    logging.basicConfig(level=getattr(logging, log_level.upper()))
    return logging.getLogger("dou")


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


def get_create_tables_file() -> str:
    create_file = os.environ.get("DB_CREATE_TABLES")
    if not create_file:
        print(os.environ)
        raise ValueError(
            f"Database create tables file not found. Please set DB_CREATE_TABLES to a valid file path. Tried '{create_file}'"
        )

    return create_file


def get_n_batch() -> int:
    n_batch_str = os.environ.get("N_BATCH", "3")
    try:
        n_batch = int(n_batch_str)
        if n_batch <= 0:
            raise ValueError
        return n_batch
    except ValueError:
        raise ValueError(
            f"Invalid N_BATCH value '{n_batch_str}'. It must be a positive integer."
        )


class Container:

    def __init__(self, usecases: dict[str, UseCase]):
        self.usecases = usecases

    @classmethod
    def create(cls) -> "Container":
        init()
        logger = get_logger()

        links_registry = create_getlink_registry()
        content_registry = create_getcontent_registry()

        db_url = get_database_url()
        create_file = get_create_tables_file()
        db_conn = SQLiteAdapter(db_url, create_file)
        links_repo = SQLLinksRepo(db_conn)

        link_collector = LinkCollector(
            registry=links_registry, links_repo=links_repo, logger=logger
        )
        link_reader = LinkReader(links_repo=links_repo, logger=logger)

        link_retry = LinkRetry(collect=link_collector, read=link_reader)

        n_batch = get_n_batch()

        content_collector = ContentCollector(
            parsers=content_registry,
            http_client=AsyncHttpx(),
            links_repo=links_repo,
            content_repo=FileContentRepoAdapter(),  # To be implemented
            logger=logger,
            n_batch=n_batch,
        )

        usecases: dict[str, UseCase] = {
            "LINKS:INSERT": link_collector,
            "LINKS:RETRY": link_retry,
            "LINKS:READ": link_reader,
            "CONTENT:INSERT": content_collector,
        }

        return cls(usecases=usecases)


def get_use_case(operation: str, command: str) -> UseCase:
    container = Container.create()
    key = f"{operation.upper()}:{command.upper()}"
    try:
        return container.usecases[key]
    except KeyError:
        raise ValueError(
            f"Invalid command '{command}'. Supported commands: {list(container.usecases.keys())}"
        )


# ---------------------------Request Response Models---------------------------
import datetime
from datetime import date
from typing import Any, Optional

from dateutil import parser as date_parser
from pydantic import BaseModel, model_validator


class LinkRequest(BaseModel):
    entity: str  # e.g., "br"
    group: str  # e.g., "dou1", "dou2", "dou3"
    start_date: date  # Will be parsed from string in validator
    end_date: Optional[date] = None  # Will be parsed from string in validator
    commit: bool = False
    status: Optional[str] = None  # e.g., "pending", "processed", "failed"
    output: Optional[str] = None  # e.g., file path for output

    @model_validator(mode="before")
    @classmethod
    def parse_dates(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # Parse start_date if it's a string
            if "start_date" in values and isinstance(values["start_date"], str):
                values["start_date"] = parse_date(values["start_date"])

            # Parse end_date if it's a string
            if "end_date" in values and isinstance(values["end_date"], str):
                values["end_date"] = parse_date(values["end_date"])

        return values


class LinkResponse(BaseModel):
    request: LinkRequest
    links: Dict[date, Any]


def parse_date(date_str: str) -> date:
    """Parse date string in multiple formats using dateutil as primary method"""
    # First try dateutil parser - it's very flexible and handles most formats
    try:
        parsed_dt = date_parser.parse(
            date_str, dayfirst=True
        )  # Assume DD/MM/YYYY format by default
        return parsed_dt.date()
    except (ValueError, TypeError):
        pass

    # Fallback to manual format parsing
    formats = [
        "%Y-%m-%d",  # 2022-12-25
        "%d/%m/%Y",  # 25/12/2022
        "%m/%d/%Y",  # 12/25/2022
        "%d-%m-%Y",  # 25-12-2022
        "%Y%m%d",  # 20221225
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    # Final fallback to ISO format
    try:
        return date.fromisoformat(date_str)
    except ValueError:
        raise ValueError(
            f"Unable to parse date '{date_str}'. Supported formats: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, DD-MM-YYYY, YYYYMMDD, and most common date formats"
        )
