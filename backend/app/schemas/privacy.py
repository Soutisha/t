from pydantic import BaseModel, Field


class ConsentUpdate(BaseModel):
    granted: bool
    policy_version: str = Field(min_length=1, max_length=30)


class AccountDeletionCreate(BaseModel):
    confirmation: str = Field(min_length=1, max_length=40)
    reason: str = Field(default="", max_length=500)


class AccountDeletionDecision(BaseModel):
    approved: bool
    note: str = Field(default="", max_length=500)


class AccountDeletionExecute(BaseModel):
    confirmation: str = Field(min_length=1, max_length=40)
