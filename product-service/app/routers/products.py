from fastapi import APIRouter, Depends, HTTPException, status
from uuid import uuid4

from ..database import products_collection, families_collection, subfamilies_collection, campaigns_collection
from ..models.product import ProductCreate, ProductResponse, ProductDetailResponse, ProductStatusUpdate
from ..security import TokenData, require_auth, require_admin, require_reviewer_or_admin, require_content_creator

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


@router.get("/", response_model=list[ProductDetailResponse])
def get_all_products(_: TokenData = Depends(require_reviewer_or_admin)):
    """All products resolved – reviewer and admin only."""
    return [_resolve(p) for p in products_collection.find()]


@router.get("/mine", response_model=list[ProductDetailResponse])
def get_my_products(current_user: TokenData = Depends(require_auth)):
    """Returns all products (resolved) where manufacturer_id matches the token owner."""
    if not current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token does not contain user id",
        )
    return [_resolve(p) for p in products_collection.find({"manufacturer_id": current_user.id})]


@router.get("/{product_id}", response_model=ProductDetailResponse)
def get_product(product_id: str, current_user: TokenData = Depends(require_auth)):
    product = products_collection.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    # Manufacturers can only see their own products
    if current_user.role == "manufacturer" and product.get("manufacturer_id") != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return _resolve(product)


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(product: ProductCreate, _: TokenData = Depends(require_content_creator)):
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
def delete_product(product_id: str, _: TokenData = Depends(require_admin)):
    result = products_collection.delete_one({"id": product_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")


VALID_TRANSITIONS: dict[str, list[str]] = {
    "reviewer": ["proposed"],
    "admin":    ["proposed", "pending"],
    "manufacturer": ["accepted", "rejected"],
}


@router.patch("/{product_id}/status", response_model=ProductDetailResponse)
def update_product_status(
    product_id: str,
    body: ProductStatusUpdate,
    current_user: TokenData = Depends(require_auth),
):
    """Update product status. Manufacturers: accepted/rejected. Reviewer/admin: proposed."""
    allowed = VALID_TRANSITIONS.get(current_user.role or "", [])
    if body.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{current_user.role}' cannot set status '{body.status}'",
        )
    doc = products_collection.find_one({"id": product_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if current_user.role == "manufacturer" and doc.get("manufacturer_id") != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    products_collection.update_one({"id": product_id}, {"$set": {"status": body.status}})
    updated = products_collection.find_one({"id": product_id})
    return _resolve(updated)

