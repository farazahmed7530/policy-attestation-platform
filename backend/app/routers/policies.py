from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Policy, PolicyVersion
from ..schemas import PolicyIn, PolicyOut, VersionIn, VersionOut

router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.get("", response_model=List[PolicyOut])
def list_policies(db: Session = Depends(get_db)):
    return db.execute(
        select(Policy).options(selectinload(Policy.versions)).order_by(Policy.name)
    ).scalars().all()


@router.post("", response_model=PolicyOut, status_code=201)
def create_policy(body: PolicyIn, db: Session = Depends(get_db)):
    if db.execute(select(Policy).where(Policy.name == body.name)).scalar_one_or_none():
        raise HTTPException(409, "A policy with that name already exists")

    policy = Policy(name=body.name, category=body.category)
    db.add(policy)
    db.flush()
    db.add(
        PolicyVersion(
            policy_id=policy.id,
            number=1,
            body=body.body,
            content_hash=PolicyVersion.hash_body(body.body),
            summary_of_changes="Initial version",
        )
    )
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/{policy_id}/versions", response_model=VersionOut, status_code=201)
def publish_version(policy_id: int, body: VersionIn, db: Session = Depends(get_db)):
    """Publishing never edits an existing version — it adds the next one.

    Existing attestations stay bound to the version they were made against, which is the
    entire point: they remain true statements about what that person agreed to.
    """
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(404, "Policy not found")

    content_hash = PolicyVersion.hash_body(body.body)
    current = policy.current_version
    if current and current.content_hash == content_hash:
        raise HTTPException(409, "That text is identical to the current version")

    version = PolicyVersion(
        policy_id=policy.id,
        number=(current.number + 1) if current else 1,
        body=body.body,
        content_hash=content_hash,
        summary_of_changes=body.summary_of_changes,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version
