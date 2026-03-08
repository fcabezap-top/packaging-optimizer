from fastapi import APIRouter, Depends, HTTPException, status
from uuid import uuid4

from ..database import containers_collection
from ..models.container import ContainerCreate, ContainerResponse, ContainerUpdate
from ..security import TokenData, require_reviewer_or_admin, require_admin

router = APIRouter(prefix="/containers", tags=["Containers"])


def _serialize(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


@router.get("/", response_model=list[ContainerResponse])
def list_containers(_: TokenData = Depends(require_reviewer_or_admin)):
    """List all active containers ordered by priority. Reviewer/admin only."""
    docs = containers_collection.find({"active": True}).sort("priority", 1)
    return [_serialize(d) for d in docs]


@router.get("/all", response_model=list[ContainerResponse])
def list_all_containers(_: TokenData = Depends(require_reviewer_or_admin)):
    """List all containers including inactive ones. Reviewer/admin only."""
    docs = containers_collection.find().sort("priority", 1)
    return [_serialize(d) for d in docs]


@router.get("/{container_id}", response_model=ContainerResponse)
def get_container(container_id: str, _: TokenData = Depends(require_reviewer_or_admin)):
    """Get a single container. Reviewer/admin only."""
    doc = containers_collection.find_one({"id": container_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")
    return _serialize(doc)


@router.post("/", response_model=ContainerResponse, status_code=status.HTTP_201_CREATED)
def create_container(container: ContainerCreate, _: TokenData = Depends(require_reviewer_or_admin)):
    """Create a new container. Priority is clamped to max_existing+1 so there are
    no gaps. If the (clamped) priority is already taken, existing containers at that
    priority and above are shifted up by one."""
    # Clamp priority: cannot exceed max_existing + 1 (avoids gaps)
    top = containers_collection.find_one(sort=[("priority", -1)])
    max_existing = top["priority"] if top else 0
    effective_priority = min(container.priority, max_existing + 1)

    # If a container already exists with the effective priority, shift all >= up by 1
    if containers_collection.find_one({"priority": effective_priority}):
        containers_collection.update_many(
            {"priority": {"$gte": effective_priority}},
            {"$inc": {"priority": 1}},
        )
    doc = container.model_dump()
    doc["id"] = str(uuid4())
    doc["priority"] = effective_priority
    containers_collection.insert_one(doc)
    return _serialize(doc)


@router.put("/{container_id}", response_model=ContainerResponse)
def update_container(
    container_id: str,
    updates: ContainerUpdate,
    _: TokenData = Depends(require_reviewer_or_admin),
):
    """Update a container. Reviewer/admin only."""
    doc = containers_collection.find_one({"id": container_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")

    patch = {k: v for k, v in updates.model_dump(exclude_unset=True).items() if v is not None}
    if not patch:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    # Si se cambia la prioridad, reordenar los demás contenedores
    new_priority = patch.get("priority")
    if new_priority is not None:
        old_priority = doc["priority"]
        if new_priority != old_priority:
            # 1) Sacar temporalmente este contenedor del sistema de prioridades
            #    asignándole un valor imposible para que no interfiera en los shifts
            containers_collection.update_one({"id": container_id}, {"$set": {"priority": -1}})

            if new_priority < old_priority:
                # Mover hacia arriba: los que están en [new_priority, old_priority-1] bajan 1
                containers_collection.update_many(
                    {"id": {"$ne": container_id}, "priority": {"$gte": new_priority, "$lt": old_priority}},
                    {"$inc": {"priority": 1}},
                )
            else:
                # Mover hacia abajo: los que están en [old_priority+1, new_priority] suben 1
                containers_collection.update_many(
                    {"id": {"$ne": container_id}, "priority": {"$gt": old_priority, "$lte": new_priority}},
                    {"$inc": {"priority": -1}},
                )

    containers_collection.update_one({"id": container_id}, {"$set": patch})
    updated = containers_collection.find_one({"id": container_id})
    return _serialize(updated)


@router.delete("/{container_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_container(container_id: str, _: TokenData = Depends(require_reviewer_or_admin)):
    """Hard delete a container and compact priorities. Reviewer/admin only."""
    doc = containers_collection.find_one({"id": container_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")

    deleted_priority = doc["priority"]
    containers_collection.delete_one({"id": container_id})

    # Shift all containers with higher priority down by 1
    containers_collection.update_many(
        {"priority": {"$gt": deleted_priority}},
        {"$inc": {"priority": -1}},
    )


# -- Local rules on a specific container --------------------------------------

from ..models.rule import LocalRule  # noqa: E402


@router.post("/{container_id}/rules", response_model=ContainerResponse, status_code=status.HTTP_201_CREATED)
def add_local_rule(
    container_id: str,
    rule: LocalRule,
    _: TokenData = Depends(require_reviewer_or_admin),
):
    """Add a local rule override to a container. Reviewer/admin only."""
    doc = containers_collection.find_one({"id": container_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")

    rule_dict = rule.model_dump()
    containers_collection.update_one(
        {"id": container_id},
        {"$push": {"local_rules": rule_dict}},
    )
    updated = containers_collection.find_one({"id": container_id})
    return _serialize(updated)


@router.delete("/{container_id}/rules/{rule_name}", response_model=ContainerResponse)
def remove_local_rule(
    container_id: str,
    rule_name: str,
    _: TokenData = Depends(require_reviewer_or_admin),
):
    """Remove a local rule from a container by name. Reviewer/admin only."""
    doc = containers_collection.find_one({"id": container_id})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Container not found")

    containers_collection.update_one(
        {"id": container_id},
        {"$pull": {"local_rules": {"name": rule_name}}},
    )
    updated = containers_collection.find_one({"id": container_id})
    return _serialize(updated)
