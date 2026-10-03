"""Schema.

The central decision is that **PolicyVersion is immutable**. A policy is a name; a version
is the actual text, frozen, with a content hash. Editing a policy never mutates a version —
it creates a new one.

That is not fussiness. An attestation is a record that a named person agreed to specific
words on a specific date. If those words can change afterwards, the record proves nothing,
and the first auditor to ask "what exactly did they sign?" ends the conversation.
"""

import hashlib
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    email: Mapped[str] = mapped_column(String(190), unique=True, index=True)
    department: Mapped[str] = mapped_column(String(64), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Policy(Base):
    """A policy is just an identity. The content lives in its versions."""

    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(190), unique=True)
    category: Mapped[str] = mapped_column(String(64), default="General")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    versions: Mapped[List["PolicyVersion"]] = relationship(
        back_populates="policy", cascade="all, delete-orphan", order_by="PolicyVersion.number"
    )

    @property
    def current_version(self) -> Optional["PolicyVersion"]:
        return self.versions[-1] if self.versions else None


class PolicyVersion(Base):
    """Immutable. Never updated after creation — only superseded."""

    __tablename__ = "policy_versions"
    __table_args__ = (UniqueConstraint("policy_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policies.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    body: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    summary_of_changes: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    policy: Mapped[Policy] = relationship(back_populates="versions")

    @staticmethod
    def hash_body(body: str) -> str:
        """Normalise whitespace before hashing: reformatting is not a change of meaning."""
        normalised = " ".join(body.split())
        return hashlib.sha256(normalised.encode()).hexdigest()


class Campaign(Base):
    """A request for a set of people to attest to one specific policy version."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_version_id: Mapped[int] = mapped_column(ForeignKey("policy_versions.id"), index=True)
    name: Mapped[str] = mapped_column(String(190))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    policy_version: Mapped[PolicyVersion] = relationship()
    attestations: Mapped[List["Attestation"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class Attestation(Base):
    """One person, one campaign, one signature.

    Stores the version's content hash alongside the foreign key. Belt and braces: even if
    the version row were somehow altered, the hash recorded at signing time would no longer
    match, and the record would show it.
    """

    __tablename__ = "attestations"
    __table_args__ = (UniqueConstraint("campaign_id", "employee_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    attested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    content_hash_at_signing: Mapped[str] = mapped_column(String(64))
    seconds_reading: Mapped[int] = mapped_column(Integer, default=0)

    campaign: Mapped[Campaign] = relationship(back_populates="attestations")
    employee: Mapped[Employee] = relationship()
