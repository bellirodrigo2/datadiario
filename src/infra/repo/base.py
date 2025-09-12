import enum

from sqlalchemy import DateTime, func
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, mapped_column

class TimestampMixin:
    @declared_attr
    def created_at(cls):
        return mapped_column(
            DateTime, default=func.now(), nullable=False
        )  # Data de criação

    @declared_attr
    def modified_at(cls):
        return mapped_column(
            DateTime, default=func.now(), onupdate=func.now(), nullable=False
        )  # Data de modificação


class Base(DeclarativeBase):
    pass