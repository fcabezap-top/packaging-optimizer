from pydantic import BaseModel, Field
from uuid import uuid4

from .family import FamilyResponse
from .subfamily import SubfamilyResponse
from .campaign import CampaignResponse


class Size(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    size_number: str  # e.g. "38", "M", "XL"
    size_name: str    # e.g. "Small", "Medium", "Euro 38"


class ProductCreate(BaseModel):
    name: str
    family_id: str
    subfamily_id: str
    campaign_id: str
    sizes: list[Size]


class ProductResponse(BaseModel):
    id: str
    name: str
    family_id: str
    subfamily_id: str
    campaign_id: str
    sizes: list[Size]


class ProductDetailResponse(BaseModel):
    """Full product with resolved references — used in GET /products/{id}."""
    id: str
    name: str
    family: FamilyResponse
    subfamily: SubfamilyResponse
    campaign: CampaignResponse
    sizes: list[Size]
