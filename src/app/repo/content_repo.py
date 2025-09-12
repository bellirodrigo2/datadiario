from datetime import date
from typing import Any, Protocol

class IContentRepo(Protocol):
    
    async def insert_content(self, entity_name: str, group: str, date: date, contents: list[dict[str,Any]]) -> dict[str,Any]: ...