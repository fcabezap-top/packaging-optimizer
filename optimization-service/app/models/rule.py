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
    #   "max_side" -> product vertical (tallest side up)
    #   "min_side" -> product horizontal (flattest side up, lying flat)
    #   "med_side" -> medium side up
    #   null       -> rotation forbidden, no specific axis enforced
    locked_axis: Optional[str] = None
    max_stack_layers: Optional[int] = None  # None = unlimited


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


class LocalRuleFilter(BaseModel):
    """Determines which products this local rule applies to inside a container.
    Empty list = applies to all families/subfamilies (no restriction).
    Fragility and campaigns are not product attributes.
    """
    family_ids: List[str] = Field(default_factory=list)
    subfamily_ids: List[str] = Field(default_factory=list)


class LocalRule(BaseModel):
    """A constraint override embedded in a Container.

    The reviewer assigns it with an explicit filter (which products it applies to)
    and the constraint it enforces, overriding any global assignment for that product.
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: Optional[str] = None
    rule_id: Optional[str] = None  # optional reference to a global catalog rule
    filter: LocalRuleFilter = Field(default_factory=LocalRuleFilter)
    constraint: RuleConstraint
