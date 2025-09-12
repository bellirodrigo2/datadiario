import enum

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import mapped_column, relationship
from ..base import Base, TimestampMixin


class LinksEntryDB(Base, TimestampMixin):
    __tablename__ = "links_entry"

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity = mapped_column(String(2), nullable=False)
    group = mapped_column(String, nullable=False)
    date = mapped_column(Date, nullable=False)

    links = relationship("LinksDB", backref="entry", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<LinksEntryDB(id={self.id}, entity={self.entity}, group={self.group}, date={self.date})>"


class LinkStatusDB(enum.Enum):
    PENDING = 0
    SUCCESS = 1
    FAILED = 2


class LinksDB(Base, TimestampMixin):
    __tablename__ = "links"

    id_link = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_entry = mapped_column(Integer, ForeignKey("links_entry.id"), nullable=False)
    link = mapped_column(Text, nullable=False)
    status = mapped_column(Enum(LinkStatusDB), nullable=False)
    msg = mapped_column(Text, nullable=True, default=None)

    def __repr__(self):
        return f"<Links(id_link={self.id_link}, id_entry={self.id_entry}, link={self.link}, status={self.status})>"
