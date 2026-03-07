from fastapi import APIRouter, Depends, HTTPException, status
from uuid import uuid4

from ..database import rules_collection
from ..models.rule import RuleCreate, RuleResponse, RuleUpdate
from ..security import TokenData, require_reviewer_or_admin, require_admin

router = APIRouter(prefix="/rules", tags=["Rules"])


def _serialize(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


@router.get("/", response_model=list[RuleResponse])
def list_rules(_: TokenData = Depends(require_reviewer_or_admin)):
    """List all active global rules. Reviewer/admin only."""
    return [_serialize(d) for d in rules_collection.find({"active": True})]


@router.get("/all", response_model=list[RuleResponse])
def list_all_rules(_: TokenData = Depends(require_reviewer_or_admin)):
    """List all global rules including inactive. Reviewer/admin only."""
    return [_serialize(d) for d in rules_collection.find()]


@router.get("/{rule_id}", response_model=RuleResponse)
def get_rule(rule_id: str, _: TokenData = Depends(require_reviewer_or_admin)):
    """Get a single rule by id. Reviewer/admin only."""
    doc = rules_collection.find_one({"id": rule_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    return _serialize(doc)


@router.post("/", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(rule: RuleCreate, _: TokenData = Depends(require_admin)):
    """Create a global rule. Admin only."""
    doc = rule.model_dump()
    doc["id"] = str(uuid4())
    rules_collection.insert_one(doc)
    return _serialize(doc)


@router.put("/{rule_id}", response_model=RuleResponse)
def update_rule(
    rule_id: str,
    updates: RuleUpdate,
    _: TokenData = Depends(require_admin),
):
    """Update a global rule. Admin only."""
    doc = rules_collection.find_one({"id": rule_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    patch = {k: v for k, v in updates.model_dump(exclude_unset=True).items() if v is not None}
    if not patch:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    rules_collection.update_one({"id": rule_id}, {"$set": patch})
    updated = rules_collection.find_one({"id": rule_id})
    return _serialize(updated)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: str, _: TokenData = Depends(require_admin)):
    """Hard delete a global rule. Admin only."""
    result = rules_collection.delete_one({"id": rule_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
