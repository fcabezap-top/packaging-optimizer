from pydantic import BaseModel


class FamilyCreate(BaseModel):
    name: str
    family_code: int


class FamilyResponse(BaseModel):
    id: str
    name: str
    family_code: int
