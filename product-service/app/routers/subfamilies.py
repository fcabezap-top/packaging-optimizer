from fastapi import APIRouter, Depends, HTTPException, status
from uuid import uuid4

from ..database import subfamilies_collection, families_collection
from ..models.subfamily import SubfamilyCreate, SubfamilyResponse
from ..security import TokenData, require_auth, require_admin

router = APIRouter(prefix="/subfamilies", tags=["Subfamilies"])


def _serialize(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


@router.get("/", response_model=list[SubfamilyResponse])
def get_all_subfamilies(_: TokenData = Depends(require_auth)):
    return [_serialize(s) for s in subfamilies_collection.find()]


@router.post("/", response_model=SubfamilyResponse, status_code=status.HTTP_201_CREATED)
def create_subfamily(subfamily: SubfamilyCreate, _: TokenData = Depends(require_admin)):
    if not families_collection.find_one({"id": subfamily.family_id}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Family not found")
    doc = subfamily.model_dump()
    doc["id"] = str(uuid4())
    subfamilies_collection.insert_one(doc)
    return _serialize(doc)


@router.delete("/{subfamily_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subfamily(subfamily_id: str, _: TokenData = Depends(require_admin)):
    result = subfamilies_collection.delete_one({"id": subfamily_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subfamily not found")
