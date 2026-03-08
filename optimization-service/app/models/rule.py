"""
Rule models.

A Rule is a named constraint that the optimization algorithm can apply
when packing inners into a container.

The rules collection is a CATALOG -- it defines what constraints exist.
It does NOT store which products each rule applies to.
The association rule <-> family/subfamily/campaign is managed in a separate
collection (rule_assignments -- to be implemented).

LocalRule is embedded inside a Container document. It overrides or adds a
constraint for a specific subset of product attributes within that container.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import uuid4


class RuleConstraint(BaseModel):
    """The actual restriction imposed by this rule."""
    orientation_locked: bool = False
    # locked_axis values when orientation_locked=True:
    #   "height" -> product vertical (tallest side up)
    #   "width"  -> product horizontal (flattest side up, lying flat)
    #   "length" -> length axis enforced
    #   null     -> rotation forbidden, no specific axis enforced
    locked_axis: Optional[str] = None
    max_stack_layers: Optional[int] = None  # None = unlimited
    max_air_pct: Optional[float] = None     # max accepted empty space % before next priority


class RuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    constraint: RuleConstraint
    active: bool = True


class RuleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    constraint: RuleConstraint
    active: bool


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    constraint: Optional[RuleConstraint] = None
    active: Optional[bool] = None


class LocalRule(BaseModel):
    """A simple named rule embedded in a Container."""
    name: str
    value: float
