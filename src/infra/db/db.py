import os
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


AsyncSessionLocal_ = None


def AsyncSessionLocal():
    return AsyncSessionLocal_()


class SqlAlchemyDB:

    def __init__(self, db: AsyncSession) -> None:
        self.db = db


@asynccontextmanager
async def init_db(_: Any):
    db_addr = os.getenv("DATABASE_URL")
    if not db_addr:
        raise ValueError("DATABASE_URL not set")

    engine = create_async_engine(
        db_addr,
        echo=False,
        # Prevent connection timeouts during long-running operations (Python 3.8)
        pool_pre_ping=True,
        # Ensure immediate data visibility across connections (Python 3.8 compatibility)
        connect_args=(
            {"check_same_thread": False} if db_addr.startswith("sqlite") else {}
        ),
    )
    global AsyncSessionLocal_
    AsyncSessionLocal_ = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    async with engine.begin() as conn:
        try:
            await conn.run_sync(Base.metadata.create_all)
            yield
        finally:
            await engine.dispose()
