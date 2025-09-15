from typing import Any, List, Optional, Tuple

import psycopg2

from .connection import DatabaseConnection


class PostgreSQLAdapter(DatabaseConnection):
    """PostgreSQL database connection adapter"""

    def __init__(
        self, connection_string: str = "postgres://postgres:123456@localhost:5432/app"
    ):
        """
        Initialize PostgreSQL connection

        Args:
            connection_string: PostgreSQL connection string
        """
        self.connection_string = connection_string
        self.connection = psycopg2.connect(self.connection_string)
        self.connection.autocommit = False  # Enable manual transaction control

    def query(
        self, statement: str, params: Optional[Tuple] = None
    ) -> List[Tuple[Any, ...]]:
        """Execute a SELECT query and return results"""
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
        """Execute an INSERT/UPDATE/DELETE statement and return affected rows or last row id"""
        cursor = self.connection.cursor()
        try:
            if params:
                cursor.execute(statement, params)
            else:
                cursor.execute(statement)

            # For INSERT with RETURNING clause, return the returned value
            if (
                statement.strip().upper().startswith("INSERT")
                and "RETURNING" in statement.upper()
            ):
                result = cursor.fetchone()
                return result[0] if result else cursor.rowcount
            else:
                return cursor.rowcount
        finally:
            cursor.close()

    def commit(self) -> None:
        """Commit the current transaction"""
        self.connection.commit()

    def rollback(self) -> None:
        """Rollback the current transaction"""
        self.connection.rollback()

    def close(self) -> None:
        """Close the database connection"""
        self.connection.close()

    def cursor(self):
        """Get a cursor for the connection"""
        return self.connection.cursor()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()
