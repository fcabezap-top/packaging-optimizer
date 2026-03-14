"""
Proposal models.

A proposal is uniquely created per (product_id + talla_id + lot_size) call.
The same product+talla can have multiple proposals over time (different lot
sizes or retries after rejection). Identity is the UUID `id`.

Lifecycle:
  pending  → accepted   (fabricante accepts the generated proposal)
  pending  → rejected   (fabricante rejects it; triggers email notification)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProposalStatus(str, Enum):
    pending  = "pending"
    accepted = "accepted"
    rejected = "rejected"


# ---------------------------------------------------------------------------
# Article (the individual packaged unit that goes into the inner box)
# ---------------------------------------------------------------------------

class ArticleDims(BaseModel):
    """Dimensions of the packaged article (the unit that enters the inner box)."""

    length_cm: float = Field(gt=0, description="First side in cm (any axis order)")
    width_cm:  float = Field(gt=0, description="Second side in cm")
    height_cm: float = Field(gt=0, description="Third side in cm")
    weight_kg: float = Field(gt=0, description="Weight per unit in kg")


# ---------------------------------------------------------------------------
# Inner box  (computed from article dims × lot_size)
# ---------------------------------------------------------------------------

class InnerBoxCalc(BaseModel):
    """
    Optimal inner box that holds exactly lot_size articles.

    Interior dims are the minimum space needed to fit the lot (articles × grid).
    Exterior dims = interior + 2 × wall_thickness per axis.
    The master optimizer receives the exterior dims to find the best container.
    """

    wall_thickness_mm: float = Field(description="Cardboard wall thickness of the inner box (mm)")

    # Interior — articles fill this space perfectly
    int_max_cm: float = Field(description="Largest interior side (cm)")
    int_med_cm: float = Field(description="Middle interior side (cm)")
    int_min_cm: float = Field(description="Smallest interior side (cm)")

    # Exterior = interior + 2×wall per axis (what the master optimizer packs)
    ext_max_cm: float = Field(description="Largest exterior side (cm)")
    ext_med_cm: float = Field(description="Middle exterior side (cm)")
    ext_min_cm: float = Field(description="Smallest exterior side (cm)")

    total_weight_kg: float = Field(description="lot_size × article weight (kg)")
    # How articles are arranged along the inner's max/med/min interior axes
    grid: List[int] = Field(
        description="[n_along_max, n_along_med, n_along_min] — articles per inner axis"
    )
    # Which article dimension (after sorting desc) maps to each inner axis
    article_axes_per_inner_axis: List[str] = Field(
        description="For each inner axis [max, med, min], which article dim is used"
    )
    fill_pct: float = 100.0  # always 100 % — articles fill the interior exactly
    air_pct: float = 0.0     # always   0 % — perfectly fitted inner box


# ---------------------------------------------------------------------------
# Master container result  (one entry per evaluated container)
# ---------------------------------------------------------------------------

class MasterResult(BaseModel):
    """Result of fitting the inner box into a specific master container."""

    container_id: str
    container_name: str
    inners_used: int
    max_by_weight: int
    grid: List[int]                # [nL, nW, nH] — inners per container axis
    inner_dims_rotated: List[float]  # [Lr, Wr, Hr] — inner orientation used
    inner_axes_used: List[str]     # ["max"/"med"/"min"] per container axis
    util_dims: List[float]         # [L_util, W_util, H_util] in cm
    ext_dims: List[float]          # [L_ext, W_ext, H_ext] in cm
    fill_pct: float
    air_pct: float
    total_weight_kg: float
    accepted: bool                 # True if this was the selected proposal
    extras: Optional[List[dict]] = None  # frontal/side prisma fill blocks for the renderer
    container_priority: Optional[int] = None


# ---------------------------------------------------------------------------
# Proposal  (the full optimization record stored in MongoDB)
# ---------------------------------------------------------------------------

class ProposalCreate(BaseModel):
    product_id: str
    size_id: str = Field(description="ID of the product size (sizes[].id from product-service)")
    article_dims: ArticleDims
    lot_size: int = Field(gt=0, description="Articles per inner box (indivisible distribution lot)")
    inner_wall_thickness_mm: float = Field(
        default=3.0, ge=0,
        description="Cardboard wall thickness for the inner box (mm). Default 3 mm.",
    )


class ProposalResponse(BaseModel):
    id: str
    product_id: str
    size_id: str
    article_dims: ArticleDims
    lot_size: int

    # Computed in step 1 (inner box calculator)
    inner_box: Optional[InnerBoxCalc] = None

    # Computed in step 2 (master optimizer)
    selected_master: Optional[MasterResult] = None
    all_evaluated: Optional[List[MasterResult]] = None

    status: ProposalStatus

    rejection_reason: Optional[str] = None

    # Generated in step 3
    render_html: Optional[str] = None
    pdf_b64:     Optional[str] = None

    created_at: datetime
    updated_at: datetime
    created_by: str


class ProposalStatusUpdate(BaseModel):
    status: ProposalStatus
    rejection_reason: Optional[str] = Field(
        default=None,
        description="Optional note when status is 'rejected'",
    )
