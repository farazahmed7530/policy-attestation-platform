"""Seed a small organisation so the app is usable the moment it starts."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Campaign, Employee, Policy, PolicyVersion

EMPLOYEES = [
    ("Amara Okafor", "amara@example.com", "Engineering"),
    ("Ben Shah", "ben@example.com", "Engineering"),
    ("Clara Nowak", "clara@example.com", "Finance"),
    ("Dmitri Volkov", "dmitri@example.com", "Sales"),
    ("Elena Rossi", "elena@example.com", "People"),
]

ACCEPTABLE_USE = """All company devices are provided for work. Reasonable personal use is
permitted, but anything unlawful, or anything that would embarrass the company if it became
public, is not.

Credentials are never shared, including with colleagues. Each person uses their own account
so that actions in our systems can be attributed to a person.

Company data is not copied to personal storage, personal email, or unapproved AI tools.
If you need to move data somewhere to do your job, ask first — the answer is usually yes,
and asking creates the record that makes it allowed."""

INFORMATION_SECURITY = """Access to production systems is granted by role and removed when
someone changes role or leaves. Nobody holds access they no longer need.

Multi-factor authentication is required on every system that supports it. Where it is not
supported, the system must be behind one that is.

Security incidents are reported immediately and without blame. Reporting something that
turns out to be nothing is always the right call; waiting to be sure is not."""


def seed(db: Session) -> bool:
    if db.execute(select(Employee).limit(1)).scalar_one_or_none():
        return False

    for name, email, department in EMPLOYEES:
        db.add(Employee(name=name, email=email, department=department))

    for name, category, body in [
        ("Acceptable Use Policy", "IT", ACCEPTABLE_USE),
        ("Information Security Policy", "Security", INFORMATION_SECURITY),
    ]:
        policy = Policy(name=name, category=category)
        db.add(policy)
        db.flush()
        db.add(
            PolicyVersion(
                policy_id=policy.id,
                number=1,
                body=body,
                content_hash=PolicyVersion.hash_body(body),
                summary_of_changes="Initial version",
            )
        )

    db.flush()

    first_version = db.execute(select(PolicyVersion).order_by(PolicyVersion.id)).scalars().first()
    db.add(
        Campaign(
            policy_version_id=first_version.id,
            name="Annual acceptable use review",
            due_at=datetime.now(timezone.utc) + timedelta(days=14),
        )
    )

    db.commit()
    return True
