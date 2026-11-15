from pydantic import BaseModel, Field

class AgentRunRequest(BaseModel):
    message: str = Field(min_length=3, max_length=2000)
    context: dict = Field(default_factory=dict)

class AgentRunFeedback(BaseModel):
    feedback: str = Field(pattern="^(helpful|not_helpful|incorrect|unsafe)$")
    comment: str = Field(default="", max_length=1000)
