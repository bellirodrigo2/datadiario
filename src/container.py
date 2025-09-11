from dataclasses import dataclass
from datetime import date, datetime
import logging
import os
from typing import Any, Callable, ClassVar, Dict, Optional

from dotenv import load_dotenv

from .app.usecase.retry import LinkRetry
from .app.usecase.getlinks import LinkCollector
from .app.usecase.readlinks import LinkReader
from .app.usecase.usecase import UseCase
from .infra.gateway.linksgateway.br import (
    get_br_dou1_links,
    get_br_dou2_links,
    get_br_dou3_links,
)
from .infra.repo.links_repo.model import Base
from .infra.repo.links_repo.repo import LinksRepo
from .infra.repo.links_repo.db import make_session

from dateutil import parser as date_parser

def create_getlink_registry() -> dict[str, Callable[..., Any]]:
    return {
        "BR:DOU1": get_br_dou1_links,
        "BR:DOU2": get_br_dou2_links,
        "BR:DOU3": get_br_dou3_links,
    }


def init():
    load_dotenv()


def get_logger():
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    logging.basicConfig(level=getattr(logging, log_level.upper()))
    return logging.getLogger("dou")


async def get_session_factory() -> Callable[..., Any]:
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
    return await make_session(db_url, Base)

@dataclass
class Container:
    link_reader: LinkReader
    link_collector: LinkCollector
    link_retry: LinkRetry
    _session_factory: ClassVar[Optional[Callable[[], Any]]] = None

    @classmethod
    async def create(cls) -> "Container":
        init()
        logger = get_logger()
        if cls._session_factory is None:
            cls._session_factory = await get_session_factory()

        registry = create_getlink_registry()
        
        links_repo = LinksRepo(cls._session_factory)
        
        link_collector = LinkCollector(
            registry=registry, links_repo=links_repo, logger=logger
        )
        link_reader = LinkReader(links_repo=links_repo, logger=logger)
        
        link_retry = LinkRetry(collect=link_collector, read=link_reader)

        return cls(link_reader=link_reader, link_collector=link_collector, link_retry=link_retry)

async def get_use_case(command: str) -> UseCase:
    container = await Container.create()
    commands_map = {
        "INSERT": container.link_collector,
        "RETRY": container.link_retry,
        "READ": container.link_reader,
    }
    usecase= commands_map.get(command.upper())
    if not usecase:
        raise ValueError(f"Invalid command '{command}'. Supported commands: {list(commands_map.keys())}")
    return usecase



#---------------------------Request Response Models---------------------------
import datetime
from typing import  Optional, Any
from pydantic import BaseModel, model_validator
from datetime import date
from dateutil import parser as date_parser
from .domain.entity.link import Link

class LinkRequest(BaseModel):
    entity: str  # e.g., "br"
    group: str  # e.g., "dou1", "dou2", "dou3"
    start_date: date  # Will be parsed from string in validator
    end_date: Optional[date] = None  # Will be parsed from string in validator
    commit: bool = False
    status: Optional[str] = None  # e.g., "pending", "processed", "failed"
    output: Optional[str] = None  # e.g., file path for output
    
    @model_validator(mode='before')
    @classmethod
    def parse_dates(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # Parse start_date if it's a string
            if 'start_date' in values and isinstance(values['start_date'], str):
                values['start_date'] = parse_date(values['start_date'])
            
            # Parse end_date if it's a string
            if 'end_date' in values and isinstance(values['end_date'], str):
                values['end_date'] = parse_date(values['end_date'])
        
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

