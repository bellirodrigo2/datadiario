from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.orm.session import Session


async def make_session(
    db_addr: str, base: type[DeclarativeBase]
) -> sessionmaker[AsyncSession]:
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

    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)

    return sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


def get_db(sessionLocal: sessionmaker[Session]):

    db = sessionLocal()
    try:
        yield db
    except Exception:
        # logger.exception("Session rollback because of exception")
        db.rollback()
        raise
    finally:
        db.close()
