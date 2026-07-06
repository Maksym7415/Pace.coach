"""Pydantic schemas for activity import API."""

from pydantic import BaseModel, Field


class ImportFitResponse(BaseModel):
    job_id: str = Field(serialization_alias="jobId")
    status: str

    model_config = {"populate_by_name": True}
