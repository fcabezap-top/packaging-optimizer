from pydantic import BaseModel


class CampaignCreate(BaseModel):
    name: str  # e.g. "Summer2025", "Winter2026"


class CampaignResponse(BaseModel):
    id: str
    name: str
