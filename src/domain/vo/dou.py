from typing import Mapping, Optional

from pydantic import BaseModel


class Dou(BaseModel):
    id: str
    gov_ent_id: str
    group: str
    edition: Optional[str]
    section: Optional[str]
    page: Optional[str]
    publication_date: str
    url: str
    title: str
    header: Mapping[str, str]
    content: str
