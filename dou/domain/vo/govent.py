from enum import Enum

from pydantic import BaseModel


class Sphere(Enum):
    FEDERAL = "Federal"
    STATE = "State"
    MUNICIPAL = "Municipal"


class GovType(Enum):
    EXECUTIVE = "Executive"
    LEGISLATIVE = "Legislative"
    JUDICIAL = "Judicial"


class GovEntity(BaseModel):
    id: str
    name: str
    acronym: str
    type: GovType
    sphere: Sphere
    country: str
