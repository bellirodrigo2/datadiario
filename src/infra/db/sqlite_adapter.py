import os
import sqlite3
from typing import Any, List, Optional, Tuple

from .connection import DatabaseConnection


class SQLiteAdapter(DatabaseConnection):
    """SQLite database connection adapter"""

    def __init__(self, database_path: str, create_file: str) -> None:
        self.database_path = database_path
        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row

        self._create_tables(create_file)

    def _create_tables(self, create_sttmt_file: str) -> None:

        with open(create_sttmt_file, "r", encoding="utf-8") as f:
            sql_content = f.read()

        cursor = self.connection.cursor()
        try:
            cursor.executescript(sql_content)
            self.connection.commit()
        finally:
            cursor.close()

    def query(
        self, statement: str, params: Optional[Tuple] = None
    ) -> List[Tuple[Any, ...]]:
        cursor = self.connection.cursor()
        try:
            if params:
                cursor.execute(statement, params)
            else:
                cursor.execute(statement)
            return cursor.fetchall()
        finally:
            cursor.close()

    def execute(self, statement: str, params: Optional[Tuple] = None) -> int:
        cursor = self.connection.cursor()
        try:
            if params:
                cursor.execute(statement, params)
            else:
                cursor.execute(statement)

            # Return lastrowid for INSERT, rowcount for UPDATE/DELETE
            if statement.strip().upper().startswith("INSERT"):
                return cursor.lastrowid
            else:
                return cursor.rowcount
        finally:
            cursor.close()

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    def close(self) -> None:
        self.connection.close()

    def cursor(self):
        return self.connection.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()
