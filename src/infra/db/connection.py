from typing import Any, List, Optional, Protocol, Tuple


class DatabaseConnection(Protocol):
    """Abstract interface for database connections"""

    def query(
        self, statement: str, params: Optional[Tuple] = None
    ) -> List[Tuple[Any, ...]]:
        """Execute a query and return results"""
        pass

    def execute(self, statement: str, params: Optional[Tuple] = None) -> int:
        """Execute a statement and return affected rows or last row id"""
        pass

    def close(self) -> None:
        """Close the database connection"""
        pass

    def commit(self) -> None:
        """Commit the current transaction"""
        pass

    def rollback(self) -> None:
        """Rollback the current transaction"""
        pass

    def cursor(self):
        """Get a cursor for the connection"""
        pass
