from datetime import date
from typing import Any, Optional, Protocol

from ...domain.service.weekdays import get_weekdays_from_range


class UseCase(Protocol):

    def execute(
        self,
        entity_name: str,
        group: str,
        start: date,
        end: Optional[date],
        commit: Optional[bool],
        status_filter: Optional[str],
    ) -> dict[date, Any]: ...

    def _get_weekdays(self, start: date, end: Optional[date]) -> list[date]:
        if end is None:
            end = start

        weekdays = get_weekdays_from_range(start, end)
        if not weekdays:
            self.logger.warning(f"No weekdays found in the range {start} to {end}.")
            return []
        return weekdays
