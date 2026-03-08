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

from typing import List, Optional
from pydantic import BaseModel, Field


class AssignmentFilter(BaseModel):
    """Selects which products this assignment applies to.
    family_id is required -- every assignment must belong to a family.
    subfamily_ids: one or more subfamilies within that family.
                   Empty list means the rule applies to the whole family.
    """
    family_id: str
    subfamily_ids: List[str] = Field(default_factory=list)


class RuleAssignmentCreate(BaseModel):
    rule_id: str
    filter: AssignmentFilter
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

