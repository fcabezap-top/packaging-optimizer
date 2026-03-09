"""
Proposals router.

Lifecycle:
  POST   /proposals/optimize          — fabricante submits article dims + lot_size
                                        → inner box computed, proposal saved as "pending"
  GET    /proposals/                  — list proposals (reviewer/admin = all; manufacturer = own)
  GET    /proposals/{id}              — get one proposal
  PATCH  /proposals/{id}/status       — accept or reject a proposal
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import requests as http_client
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..config import PRODUCT_SERVICE_URL
from ..database import proposals_collection, containers_collection
from ..engine.inner_calculator import compute_inner_box
from ..engine.master_optimizer import run_master_pipeline
from ..models.proposal import (
    ProposalCreate,
    ProposalResponse,
    ProposalStatus,
    ProposalStatusUpdate,
)
from ..security import TokenData, require_auth, oauth2_scheme

router = APIRouter(prefix="/proposals", tags=["Proposals"])


def _serialize(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


def _validate_product_and_ownership(
    product_id: str, size_id: str, current_user: TokenData, token: str
) -> None:
    """
    Calls product-service to verify:
      1. The product exists.
      2. The size_id belongs to that product.
      3. The token user is the product's manufacturer (manufacturer only).
    Raises HTTPException on any violation.
    """
    try:
        resp = http_client.get(
            f"{PRODUCT_SERVICE_URL}/products/{product_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
    except http_client.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Product service unreachable: {exc}",
        )

    if resp.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{product_id}' not found",
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response from product service",
        )

    product = resp.json()

    # Check size_id exists in this product
    size_ids = [s["id"] for s in product.get("sizes", [])]
    if size_id not in size_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Size '{size_id}' does not belong to product '{product_id}'",
        )

    # Manufacturers can only optimize their own products
    if current_user.role == "manufacturer":
        user_key = current_user.id or current_user.username
        if product.get("manufacturer_id") != user_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not the manufacturer of this product",
            )


# ---------------------------------------------------------------------------
# POST /proposals/optimize
# ---------------------------------------------------------------------------

@router.post(
    "/optimize",
    response_model=ProposalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Full optimization pipeline: article → inner box → master container",
)
def create_proposal(
    body: ProposalCreate,
    current_user: TokenData = Depends(require_auth),
    token: str = Depends(oauth2_scheme),
):
    """
    Full optimization pipeline (one shot):
      1. Validate product existence + manufacturer ownership via product-service.
      2. Calculate the optimal inner box (article dims × lot_size + cardboard wall).
      3. Run the master container optimizer over all active containers.
      4. Save the complete proposal (inner + master) as 'pending'.
    """
    _validate_product_and_ownership(body.product_id, body.size_id, current_user, token)

    inner = compute_inner_box(
        length_cm=body.article_dims.length_cm,
        width_cm=body.article_dims.width_cm,
        height_cm=body.article_dims.height_cm,
        weight_kg=body.article_dims.weight_kg,
        lot_size=body.lot_size,
        wall_thickness_mm=body.inner_wall_thickness_mm,
    )
    if inner is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not compute inner box: invalid dimensions or lot_size",
        )

    # Load active containers ordered by priority (ascending = try smallest first)
    containers = list(containers_collection.find({"active": True}).sort("priority", 1))

    selected_master, all_evaluated = run_master_pipeline(
        inner_ext=(inner.ext_max_cm, inner.ext_med_cm, inner.ext_min_cm),
        inner_weight_kg=inner.total_weight_kg,
        containers=containers,
    )

    now = datetime.now(timezone.utc)
    doc = {
        "id": str(uuid4()),
        "product_id": body.product_id,
        "size_id": body.size_id,
        "article_dims": body.article_dims.model_dump(),
        "lot_size": body.lot_size,
        "inner_box": inner.model_dump(),
        "selected_master": selected_master.model_dump() if selected_master else None,
        "all_evaluated": [r.model_dump() for r in all_evaluated],
        "status": ProposalStatus.pending.value,
        "rejection_reason": None,
        "render_html": None,
        "pdf_b64": None,
        "created_at": now,
        "updated_at": now,
        "created_by": current_user.id or current_user.username,
    }
    proposals_collection.insert_one(doc)
    return _serialize(doc)


# ---------------------------------------------------------------------------
# GET /proposals/
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=list[ProposalResponse],
    summary="List proposals",
)
def list_proposals(
    product_id: Optional[str] = Query(default=None),
    size_id: Optional[str] = Query(default=None),
    proposal_status: Optional[ProposalStatus] = Query(default=None, alias="status"),
    current_user: TokenData = Depends(require_auth),
):
    """
    Reviewer/admin sees all proposals.
    Manufacturer sees only proposals created by themselves.
    """
    query: dict = {}

    if current_user.role == "manufacturer":
        query["created_by"] = current_user.id or current_user.username

    if product_id:
        query["product_id"] = product_id
    if size_id:
        query["size_id"] = size_id
    if proposal_status:
        query["status"] = proposal_status.value

    docs = proposals_collection.find(query).sort("created_at", -1)
    return [_serialize(d) for d in docs]


# ---------------------------------------------------------------------------
# GET /proposals/{id}
# ---------------------------------------------------------------------------

@router.get(
    "/{proposal_id}",
    response_model=ProposalResponse,
    summary="Get a single proposal",
)
def get_proposal(
    proposal_id: str,
    current_user: TokenData = Depends(require_auth),
):
    doc = proposals_collection.find_one({"id": proposal_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")

    # Manufacturer can only read own proposals
    if current_user.role == "manufacturer":
        owner = doc.get("created_by")
        user_key = current_user.id or current_user.username
        if owner != user_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: not your proposal",
            )

    return _serialize(doc)


# ---------------------------------------------------------------------------
# PATCH /proposals/{id}/status
# ---------------------------------------------------------------------------

@router.patch(
    "/{proposal_id}/status",
    response_model=ProposalResponse,
    summary="Accept or reject a proposal",
)
def update_status(
    proposal_id: str,
    body: ProposalStatusUpdate,
    current_user: TokenData = Depends(require_auth),
):
    """
    Transitions:
      pending → accepted   (fabricante accepts)
      pending → rejected   (fabricante rejects; rejection_reason required)

    Manufacturer can only update own proposals.
    Reviewer/admin can update any.
    """
    doc = proposals_collection.find_one({"id": proposal_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")

    if current_user.role == "manufacturer":
        owner = doc.get("created_by")
        user_key = current_user.id or current_user.username
        if owner != user_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: not your proposal",
            )

    patch = {
        "status": body.status.value,
        "rejection_reason": body.rejection_reason,
        "updated_at": datetime.now(timezone.utc),
    }
    proposals_collection.update_one({"id": proposal_id}, {"$set": patch})

    updated = proposals_collection.find_one({"id": proposal_id})
    return _serialize(updated)
