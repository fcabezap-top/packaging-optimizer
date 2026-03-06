from fastapi import APIRouter, HTTPException, status
from uuid import uuid4

from ..database import products_collection, families_collection, subfamilies_collection, campaigns_collection
from ..models.product import ProductCreate, ProductResponse, ProductDetailResponse
from ..models.family import FamilyResponse
from ..models.subfamily import SubfamilyResponse
from ..models.campaign import CampaignResponse

router = APIRouter(prefix="/products", tags=["Products"])


def _serialize(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


def _resolve(product: dict) -> dict:
    """Resolve family_id, subfamily_id and campaign_id to full objects."""
    family = families_collection.find_one({"id": product["family_id"]})
    subfamily = subfamilies_collection.find_one({"id": product["subfamily_id"]})
    campaign = campaigns_collection.find_one({"id": product["campaign_id"]})
    return {
        **_serialize(product),
        "family": _serialize(family) if family else {"id": product["family_id"], "name": "Unknown", "family_code": 0},
        "subfamily": _serialize(subfamily) if subfamily else {"id": product["subfamily_id"], "name": "Unknown", "subfamily_code": 0, "family_id": ""},
        "campaign": _serialize(campaign) if campaign else {"id": product["campaign_id"], "name": "Unknown"},
    }


@router.get("/", response_model=list[ProductResponse])
def get_all_products():
    return [_serialize(p) for p in products_collection.find()]


@router.get("/{product_id}", response_model=ProductDetailResponse)
def get_product(product_id: str):
    product = products_collection.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return _resolve(product)


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(product: ProductCreate):
    if not families_collection.find_one({"id": product.family_id}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Family not found")
    subfamily = subfamilies_collection.find_one({"id": product.subfamily_id})
    if not subfamily:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subfamily not found")
    if subfamily.get("family_id") != product.family_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subfamily does not belong to the given family")
    if not campaigns_collection.find_one({"id": product.campaign_id}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign not found")

    doc = product.model_dump()
    doc["id"] = str(uuid4())
    products_collection.insert_one(doc)
    return _serialize(doc)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: str):
    result = products_collection.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

