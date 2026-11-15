from pydantic import BaseModel, Field, ConfigDict

class SkillCreate(BaseModel):
    skill_name: str = Field(min_length=2, max_length=100)
    years_experience: int = Field(default=0, ge=0, le=60)

class VisibilityUpdate(BaseModel):
    enabled: bool
    consent_version: str = Field(min_length=1, max_length=30)

class VerificationUpdate(BaseModel):
    approved: bool
