from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Attestation, Campaign, Employee
from ..schemas import OutstandingItem

router = APIRouter(prefix="/api", tags=["reports"])


def _aware(moment: datetime) -> datetime:
    """SQLite returns naive datetimes; everything is stored in UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


@router.get("/employees/{employee_id}/outstanding", response_model=List[OutstandingItem])
def outstanding_for_employee(employee_id: int, db: Session = Depends(get_db)):
    """What this person still has to sign."""
    if not db.get(Employee, employee_id):
        raise HTTPException(404, "Employee not found")

    signed = set(
        db.execute(
            select(Attestation.campaign_id).where(Attestation.employee_id == employee_id)
        ).scalars().all()
    )

    campaigns = db.execute(
        select(Campaign).options(selectinload(Campaign.policy_version))
    ).scalars().all()

    now = datetime.now(timezone.utc)
    items = []
    for campaign in campaigns:
        if campaign.id in signed:
            continue
        version = campaign.policy_version
        items.append(
            OutstandingItem(
                campaign_id=campaign.id,
                campaign_name=campaign.name,
                policy_name=version.policy.name,
                version_number=version.number,
                due_at=campaign.due_at,
                overdue=_aware(campaign.due_at) < now,
                body=version.body,
            )
        )
    return items


@router.get("/campaigns/{campaign_id}/completion")
def campaign_completion(campaign_id: int, db: Session = Depends(get_db)):
    """Who has signed, who has not, and what exactly they agreed to."""
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    employees = db.execute(select(Employee).where(Employee.active.is_(True))).scalars().all()
    attestations = {
        attestation.employee_id: attestation
        for attestation in db.execute(
            select(Attestation).where(Attestation.campaign_id == campaign_id)
        ).scalars().all()
    }

    version = campaign.policy_version
    signed, outstanding = [], []

    for employee in employees:
        attestation = attestations.get(employee.id)
        if attestation:
            signed.append(
                {
                    "name": employee.name,
                    "email": employee.email,
                    "department": employee.department,
                    "attested_at": attestation.attested_at,
                    "seconds_reading": attestation.seconds_reading,
                    # If this ever differs from the version's hash, the version was tampered with.
                    "hash_matches_version": attestation.content_hash_at_signing
                    == version.content_hash,
                }
            )
        else:
            outstanding.append(
                {"name": employee.name, "email": employee.email, "department": employee.department}
            )

    total = len(employees)
    return {
        "campaign": campaign.name,
        "policy": version.policy.name,
        "version": version.number,
        "content_hash": version.content_hash,
        "due_at": campaign.due_at,
        "overdue": _aware(campaign.due_at) < datetime.now(timezone.utc),
        "summary": {
            "total": total,
            "signed": len(signed),
            "outstanding": len(outstanding),
            "completion_percent": round(len(signed) / total * 100, 1) if total else 0.0,
        },
        "signed": signed,
        "chase_list": outstanding,
    }
