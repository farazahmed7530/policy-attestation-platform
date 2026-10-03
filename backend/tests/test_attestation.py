"""The invariant under test: an attestation stays bound to the exact words that were signed.

Everything else here is CRUD. This is the part that makes the record evidence.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.seed import seed


@pytest.fixture()
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    with TestSession() as session:
        seed(session)

    def override():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_publishing_a_new_version_does_not_alter_the_old_one(client):
    policy = client.get("/api/policies").json()[0]
    original = policy["versions"][0]

    client.post(
        f"/api/policies/{policy['id']}/versions",
        json={"body": "Completely different text about acceptable use.", "summary_of_changes": "Rewrite"},
    )

    after = next(p for p in client.get("/api/policies").json() if p["id"] == policy["id"])
    assert len(after["versions"]) == 2
    assert after["versions"][0]["body"] == original["body"]
    assert after["versions"][0]["content_hash"] == original["content_hash"]


def test_an_attestation_survives_the_policy_being_rewritten(client):
    campaign = client.get("/api/campaigns").json()[0]
    employee = client.get("/api/employees").json()[0]

    signed = client.post(
        f"/api/campaigns/{campaign['id']}/attest",
        json={"employee_id": employee["id"], "seconds_reading": 42},
    ).json()

    policy = client.get("/api/policies").json()[0]
    client.post(
        f"/api/policies/{policy['id']}/versions",
        json={"body": "Rewritten after the fact.", "summary_of_changes": "Sneaky"},
    )

    completion = client.get(f"/api/campaigns/{campaign['id']}/completion").json()
    record = completion["signed"][0]

    # The campaign still points at the version that was actually signed.
    assert completion["content_hash"] == signed["content_hash"]
    assert record["hash_matches_version"] is True


def test_republishing_identical_text_is_rejected(client):
    policy = client.get("/api/policies").json()[0]
    body = policy["versions"][0]["body"]

    response = client.post(f"/api/policies/{policy['id']}/versions", json={"body": body})
    assert response.status_code == 409


def test_reformatting_is_not_treated_as_a_change(client):
    policy = client.get("/api/policies").json()[0]
    reflowed = policy["versions"][0]["body"].replace("\n", "  ")

    response = client.post(f"/api/policies/{policy['id']}/versions", json={"body": reflowed})
    assert response.status_code == 409, "whitespace-only edits must not create a new version"


def test_nobody_can_attest_twice(client):
    campaign = client.get("/api/campaigns").json()[0]
    employee = client.get("/api/employees").json()[0]
    payload = {"employee_id": employee["id"], "seconds_reading": 10}

    assert client.post(f"/api/campaigns/{campaign['id']}/attest", json=payload).status_code == 201
    assert client.post(f"/api/campaigns/{campaign['id']}/attest", json=payload).status_code == 409


def test_outstanding_list_shrinks_when_someone_signs(client):
    campaign = client.get("/api/campaigns").json()[0]
    employee = client.get("/api/employees").json()[0]

    before = client.get(f"/api/employees/{employee['id']}/outstanding").json()
    assert any(item["campaign_id"] == campaign["id"] for item in before)

    client.post(f"/api/campaigns/{campaign['id']}/attest", json={"employee_id": employee["id"]})

    after = client.get(f"/api/employees/{employee['id']}/outstanding").json()
    assert not any(item["campaign_id"] == campaign["id"] for item in after)


def test_completion_reports_who_still_needs_chasing(client):
    campaign = client.get("/api/campaigns").json()[0]
    employees = client.get("/api/employees").json()

    for employee in employees[:2]:
        client.post(f"/api/campaigns/{campaign['id']}/attest", json={"employee_id": employee["id"]})

    completion = client.get(f"/api/campaigns/{campaign['id']}/completion").json()
    assert completion["summary"]["signed"] == 2
    assert completion["summary"]["outstanding"] == len(employees) - 2
    assert len(completion["chase_list"]) == len(employees) - 2
