from pydantic import BaseModel


class FamilyCreate(BaseModel):
    name: str


class FamilyResponse(BaseModel):
    id: str
    name: str
