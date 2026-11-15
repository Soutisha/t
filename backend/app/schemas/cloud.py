from typing import Literal
from pydantic import BaseModel, Field, HttpUrl

class IntegrationCreate(BaseModel):
    provider: Literal["erpnext", "sap", "dynamics365", "webhook", "s3"]
    connection_name: str = Field(min_length=2, max_length=100)
    environment: Literal["sandbox", "production"] = "sandbox"
    base_url: str = Field(default="", max_length=500)
    credential_env_key: str = Field(default="", pattern=r"^[A-Z][A-Z0-9_]{2,99}$")
    config: dict = Field(default_factory=dict)

class OutboxEventCreate(BaseModel):
    event_type: str = Field(min_length=3, max_length=100)
    aggregate_type: str = Field(default="", max_length=60)
    aggregate_id: str = Field(default="", max_length=36)
    payload: dict = Field(default_factory=dict)

class SyncRequest(BaseModel):
    operation: Literal["health_check", "pull_catalogue", "push_inventory", "pull_orders"]
