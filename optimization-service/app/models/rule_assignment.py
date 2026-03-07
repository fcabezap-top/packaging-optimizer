"""
RuleAssignment models.

A RuleAssignment links a global catalog rule to a set of product attributes
(family, subfamily, campaign, fragility).

This separates the WHAT (rule constraint, defined in the rules catalog) from
the WHEN/WHERE (which products the rule applies to, defined here).

Lifecycle of a rule enforcement:
  1. Admin/reviewer creates a Rule in the catalog (what constraint to apply).
  2. Admin/reviewer creates a RuleAssignment linking that rule to a filter
     (which families/subfamilies/campaigns/fragility it applies to).
  3. The optimization engine, when processing a batch, queries active assignments
     that match the product's attributes and applies the corresponding constraints.

`active` on the assignment enables soft-disabling an assignment without deleting
it (e.g. a seasonal campaign rule that is paused between seasons).
"""

from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field


class AssignmentFilter(BaseModel):
    """Selects which products this assignment applies to.
    Empty list = no restriction on that dimension (applies to all families/subfamilies).
    Fragility and campaigns are not product attributes -- they are determined
    implicitly by belonging to a family or subfamily.
    """
    family_ids: List[str] = Field(default_factory=list)
    subfamily_ids: List[str] = Field(default_factory=list)


class RuleAssignmentCreate(BaseModel):
    rule_id: str
    filter: AssignmentFilter = Field(default_factory=AssignmentFilter)
    active: bool = True


class RuleAssignmentResponse(BaseModel):
    id: str
    rule_id: str
    filter: AssignmentFilter
    active: bool


class RuleAssignmentUpdate(BaseModel):
    rule_id: Optional[str] = None
    filter: Optional[AssignmentFilter] = None
    active: Optional[bool] = None

