from fastapi import APIRouter, Depends, HTTPException, status
from uuid import uuid4

from ..database import campaigns_collection
from ..models.campaign import CampaignCreate, CampaignResponse
from ..security import TokenData, require_auth, require_admin

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


def _serialize(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


@router.get("/", response_model=list[CampaignResponse])
def get_all_campaigns(_: TokenData = Depends(require_auth)):
    return [_serialize(c) for c in campaigns_collection.find()]


@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(campaign: CampaignCreate, _: TokenData = Depends(require_admin)):
    doc = campaign.model_dump()
    doc["id"] = str(uuid4())
    campaigns_collection.insert_one(doc)
    return _serialize(doc)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign_id: str, _: TokenData = Depends(require_admin)):
    result = campaigns_collection.delete_one({"id": campaign_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
