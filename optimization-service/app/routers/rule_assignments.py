from fastapi import APIRouter, Depends, HTTPException, status
from uuid import uuid4

from ..database import rule_assignments_collection, rules_collection
from ..models.rule_assignment import (
    RuleAssignmentCreate,
    RuleAssignmentResponse,
    RuleAssignmentUpdate,
)
from ..security import TokenData, require_auth, require_reviewer_or_admin, require_admin

router = APIRouter(prefix="/rule-assignments", tags=["Rule Assignments"])


def _serialize(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


def _check_rule_exists(rule_id: str) -> None:
    if not rules_collection.find_one({"id": rule_id}):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule '{rule_id}' not found in catalog",
        )


# ---------------------------------------------------------------------------
# Read endpoints — any authenticated user (needed by the optimizer)
# ---------------------------------------------------------------------------


@router.get("/", response_model=list[RuleAssignmentResponse])
def list_active_assignments(_: TokenData = Depends(require_auth)):
    """List all active assignments. Any authenticated user."""
    return [_serialize(d) for d in rule_assignments_collection.find({"active": True})]


@router.get("/all", response_model=list[RuleAssignmentResponse])
def list_all_assignments(_: TokenData = Depends(require_reviewer_or_admin)):
    """List all assignments including inactive. Reviewer/admin only."""
    return [_serialize(d) for d in rule_assignments_collection.find()]


@router.get("/by-rule/{rule_id}", response_model=list[RuleAssignmentResponse])
def list_by_rule(rule_id: str, _: TokenData = Depends(require_auth)):
    """All active assignments for a specific catalog rule."""
    _check_rule_exists(rule_id)
    return [
        _serialize(d)
        for d in rule_assignments_collection.find({"rule_id": rule_id, "active": True})
    ]


@router.get("/by-family/{family_id}", response_model=list[RuleAssignmentResponse])
def list_by_family(family_id: str, _: TokenData = Depends(require_auth)):
    """All active assignments for a given family_id."""
    return [
        _serialize(d)
        for d in rule_assignments_collection.find(
            {"filter.family_id": family_id, "active": True}
        )
    ]


@router.get("/by-subfamily/{subfamily_id}", response_model=list[RuleAssignmentResponse])
def list_by_subfamily(subfamily_id: str, _: TokenData = Depends(require_auth)):
    """All active assignments that include a given subfamily_id in their filter."""
    return [
        _serialize(d)
        for d in rule_assignments_collection.find(
            {"filter.subfamily_ids": subfamily_id, "active": True}
        )
    ]


@router.get("/{assignment_id}", response_model=RuleAssignmentResponse)
def get_assignment(assignment_id: str, _: TokenData = Depends(require_auth)):
    doc = rule_assignments_collection.find_one({"id": assignment_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return _serialize(doc)


# ---------------------------------------------------------------------------
# Write endpoints — reviewer/admin (create, update) or admin (delete)
# ---------------------------------------------------------------------------


@router.post("/", response_model=RuleAssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    assignment: RuleAssignmentCreate,
    _: TokenData = Depends(require_reviewer_or_admin),
):
    """Create an assignment linking a rule to a product filter. Reviewer/admin."""
    _check_rule_exists(assignment.rule_id)
    doc = assignment.model_dump()
    doc["id"] = str(uuid4())
    rule_assignments_collection.insert_one(doc)
    return _serialize(doc)


@router.put("/{assignment_id}", response_model=RuleAssignmentResponse)
def update_assignment(
    assignment_id: str,
    updates: RuleAssignmentUpdate,
    _: TokenData = Depends(require_reviewer_or_admin),
):
    """Update an assignment. Reviewer/admin."""
    doc = rule_assignments_collection.find_one({"id": assignment_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    patch = updates.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    if "rule_id" in patch:
        _check_rule_exists(patch["rule_id"])

    rule_assignments_collection.update_one({"id": assignment_id}, {"$set": patch})
    updated = rule_assignments_collection.find_one({"id": assignment_id})
    return _serialize(updated)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(assignment_id: str, _: TokenData = Depends(require_reviewer_or_admin)):
    """Hard delete an assignment. Reviewer/admin only."""
    result = rule_assignments_collection.delete_one({"id": assignment_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
