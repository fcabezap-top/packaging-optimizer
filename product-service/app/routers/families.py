from fastapi import APIRouter, HTTPException, status
from uuid import uuid4

from ..database import families_collection
from ..models.family import FamilyCreate, FamilyResponse

router = APIRouter(prefix="/families", tags=["Families"])


def _serialize(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


@router.get("/", response_model=list[FamilyResponse])
def get_all_families():
    return [_serialize(f) for f in families_collection.find()]


@router.post("/", response_model=FamilyResponse, status_code=status.HTTP_201_CREATED)
def create_family(family: FamilyCreate):
    doc = family.model_dump()
    doc["id"] = str(uuid4())
    families_collection.insert_one(doc)
    return _serialize(doc)


@router.delete("/{family_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_family(family_id: str):
    result = families_collection.delete_one({"id": family_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family not found")
