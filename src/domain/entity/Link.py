from datetime import date
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl, model_validator


class LinkStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


def init_not_allowed():
    folder = Path(__file__).parent
    notallowed_file = (folder / "notallowed.json").resolve()
    with open(notallowed_file) as f:
        import json

        data = json.load(f)
        notallowed = data.get("not_allowed", [])

    return notallowed


NOT_ALLOWED = init_not_allowed()


def check_not_allowed(link: str) -> None:

    for substring in NOT_ALLOWED:
        if substring in link:
            raise ValueError(f"Link contains not allowed substring: {substring}")


class Link(BaseModel):
    link: str
    status: LinkStatus = Field(default=LinkStatus.PENDING)

    @model_validator(mode="after")
    def validate_link(self) -> "Link":
        try:
            HttpUrl(url=self.link)
            check_not_allowed(self.link)
        except ValueError:
            self.status = LinkStatus.FAILED
        return self

    def process_link(self) -> None:
        if self.status == LinkStatus.PENDING:
            self.status = LinkStatus.PROCESSED
            return
        elif self.status == LinkStatus.FAILED:
            raise ValueError("Cannot process a failed link")
        raise ValueError("Link already processed")


class LinksEntry(BaseModel):
    entity: str
    group: str
    date: date
    links: list[Link]

    @property
    def links_str(self) -> list[str]:
        return [link.link for link in self.links]
