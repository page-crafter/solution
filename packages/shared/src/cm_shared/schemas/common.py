from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class OrmModel(BaseModel):
    """Base schema that can serialize SQLAlchemy ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class JobEventRead(OrmModel):
    """Serialize a job progress event for polling clients."""

    id: int
    job_id: str
    level: str
    message: str
    created_at: datetime


class TaskExecutionRead(OrmModel):
    """Serialize a persisted worker task execution for the Runs page."""

    id: int
    job_id: str
    task_id: Optional[str] = None
    task_name: str
    actor: str
    status: str
    message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    updated_at: datetime


class JobRead(OrmModel):
    """Serialize the visible status of an asynchronous job."""

    id: str
    status: str
    task_id: Optional[str] = None
    message: Optional[str] = None
