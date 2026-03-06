from pydantic import BaseModel, Field
from uuid import uuid4

from .family import FamilyResponse
from .subfamily import SubfamilyResponse
from .campaign import CampaignResponse


class Size(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str   # e.g. "S", "M", "XL", "9W", "64GB", "120cm"
    order: int  # sequential position starting at 0


class ProductCreate(BaseModel):
    name: str
    description: str
    ean_code: str
    manufacturer_id: str
    family_id: str
    subfamily_id: str
    campaign_id: str
    sizes: list[Size]


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str
    ean_code: str
    manufacturer_id: str
    family_id: str
    subfamily_id: str
    campaign_id: str
    sizes: list[Size]


class ProductDetailResponse(BaseModel):
    """Full product with resolved references — used in GET /products/{id}."""
    id: str
    name: str
    description: str
    ean_code: str
    manufacturer_id: str
    family_id: str
    subfamily_id: str
    campaign_id: str
    sizes: list[Size]
    family: FamilyResponse
    subfamily: SubfamilyResponse
    campaign: CampaignResponse
