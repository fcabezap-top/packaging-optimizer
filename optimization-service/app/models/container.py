"""
Container models.

A container is a master box whose dimensions are defined as ranges per axis.
Sides are named by their relative size: max_side, med_side, min_side.
A fixed dimension is expressed as min == max.
The optimization algorithm tries each active container ordered by priority
and picks the best proposal (highest fill%).

dims_cm ranges are the INTERIOR usable space.
wall_thickness_mm is the cardboard thickness — the algorithm discounts
  2 * wall_thickness_mm / 10  cm per axis from each dim range.
inner_margin_cm adds operational clearance per axis on top of the wall discount.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from uuid import uuid4

from .rule import LocalRule


class DimRange(BaseModel):
    min: float = Field(gt=0)
    max: float = Field(gt=0)

    @model_validator(mode="after")
    def min_lte_max(self) -> "DimRange":
        if self.min > self.max:
            raise ValueError("min must be <= max")
        return self


class ContainerDims(BaseModel):
    max_side: DimRange
    med_side: DimRange
    min_side: DimRange


class InnerMargin(BaseModel):
    max_side: float = Field(default=0.5, ge=0)
    med_side: float = Field(default=0.5, ge=0)
    min_side: float = Field(default=0.5, ge=0)


class ContainerCreate(BaseModel):
    name: str
    description: Optional[str] = None
    dims_cm: ContainerDims
    wall_thickness_mm: float = Field(default=3.0, ge=0)
    inner_margin_cm: InnerMargin = Field(default_factory=InnerMargin)
    max_weight_kg: float = Field(gt=0)
    priority: int = Field(default=1, ge=1)
    active: bool = True
    local_rules: List[LocalRule] = Field(default_factory=list)


class ContainerResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    dims_cm: ContainerDims
    wall_thickness_mm: float
    inner_margin_cm: InnerMargin
    max_weight_kg: float
    priority: int
    active: bool
    local_rules: List[LocalRule]


class ContainerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    dims_cm: Optional[ContainerDims] = None
    wall_thickness_mm: Optional[float] = Field(default=None, ge=0)
    inner_margin_cm: Optional[InnerMargin] = None
    max_weight_kg: Optional[float] = Field(default=None, gt=0)
    priority: Optional[int] = Field(default=None, ge=1)
    active: Optional[bool] = None
    local_rules: Optional[List[LocalRule]] = None
