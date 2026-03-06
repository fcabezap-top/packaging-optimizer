from pydantic import BaseModel


class SubfamilyCreate(BaseModel):
    name: str
    subfamily_code: int
    family_id: str


class SubfamilyResponse(BaseModel):
    id: str
    name: str
    subfamily_code: int
    family_id: str
