from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Attestation, Campaign, Employee, PolicyVersion
from ..schemas import AttestationIn, CampaignIn, CampaignOut

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.get("", response_model=List[CampaignOut])
def list_campaigns(db: Session = Depends(get_db)):
    return db.execute(
        select(Campaign)
        .options(selectinload(Campaign.policy_version))
        .order_by(Campaign.created_at.desc())
    ).scalars().all()


@router.post("", response_model=CampaignOut, status_code=201)
def launch_campaign(body: CampaignIn, db: Session = Depends(get_db)):
    version = db.get(PolicyVersion, body.policy_version_id)
    if not version:
        raise HTTPException(404, "Policy version not found")

    campaign = Campaign(
        policy_version_id=version.id,
        name=body.name,
        due_at=datetime.now(timezone.utc) + timedelta(days=body.due_in_days),
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/attest", status_code=201)
def attest(campaign_id: int, body: AttestationIn, db: Session = Depends(get_db)):
    """Record that this person agreed to this exact text.

    The version's content hash is copied onto the attestation. The foreign key says which
    version; the hash says what that version said at the moment of signing.
    """
    campaign = db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    employee = db.get(Employee, body.employee_id)
    if not employee:
        raise HTTPException(404, "Employee not found")

    existing = db.execute(
        select(Attestation).where(
            Attestation.campaign_id == campaign_id,
            Attestation.employee_id == body.employee_id,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Already attested")

    version = db.get(PolicyVersion, campaign.policy_version_id)
    attestation = Attestation(
        campaign_id=campaign_id,
        employee_id=body.employee_id,
        content_hash_at_signing=version.content_hash,
        seconds_reading=body.seconds_reading,
    )
    db.add(attestation)
    db.commit()

    return {
        "attested": True,
        "policy": version.policy.name,
        "version": version.number,
        "content_hash": version.content_hash,
    }
