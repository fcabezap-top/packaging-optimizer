from pydantic import BaseModel


class SubfamilyCreate(BaseModel):
    name: str
    family_id: str


class SubfamilyResponse(BaseModel):
    id: str
    name: str
    family_id: str
