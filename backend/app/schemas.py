from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    department: str


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    number: int
    body: str
    content_hash: str
    summary_of_changes: str
    published_at: datetime


class PolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    category: str
    versions: List[VersionOut] = []


class PolicyIn(BaseModel):
    name: str
    category: str = "General"
    body: str


class VersionIn(BaseModel):
    body: str
    summary_of_changes: str = ""


class CampaignIn(BaseModel):
    policy_version_id: int
    name: str
    due_in_days: int = 14


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    due_at: datetime
    policy_version: VersionOut


class AttestationIn(BaseModel):
    employee_id: int
    seconds_reading: int = 0


class OutstandingItem(BaseModel):
    campaign_id: int
    campaign_name: str
    policy_name: str
    version_number: int
    due_at: datetime
    overdue: bool
    body: Optional[str] = None
