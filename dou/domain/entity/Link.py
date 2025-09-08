from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class LinkStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


folder = Path(__file__).parent
notallowed_file = folder / "notallowed.json"
with open(notallowed_file) as f:
    import json

    data = json.load(f)
    NOT_ALLOWED = data.get("not_allowed", [])


def check_not_allowed(link: str) -> None:

    for substring in NOT_ALLOWED:
        if substring in link:
            raise ValueError(f"Link contains not allowed substring: {substring}")


class Link(BaseModel):
    link: str
    status: LinkStatus = Field(default=LinkStatus.PENDING)

    def __post_init__(self):
        try:
            HttpUrl(url=self.link)
            check_not_allowed(self.link)
        except ValueError:
            self.status = LinkStatus.FAILED

    def process_link(self) -> None:
        if self.status == LinkStatus.PENDING:
            self.status = LinkStatus.PROCESSED
            return
        elif self.status == LinkStatus.FAILED:
            raise ValueError("Cannot process a failed link")
        raise ValueError("Link already processed")

    def compare(self, other: "Link") -> Optional["Link"]:
        if self.status == LinkStatus.FAILED and other.status != LinkStatus.FAILED:
            return other
