from datetime import date
from typing import Any, Optional, Protocol

class UseCase(Protocol):

    def execute(
        self,
        entity_name: str,
        group: str,
        start: date,
        end: Optional[date],
        commit: Optional[bool],
        status_filter: Optional[str],
    ) -> Any: ...
