from pydantic import BaseModel, Field

class CopilotQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    language: str = Field(default="auto", pattern="^(auto|en|hi|bn|ta|te|kn|ml|mr)$")

class CopilotFeedback(BaseModel):
    feedback: str = Field(pattern="^(helpful|not_helpful|incorrect|missing_source)$")
    comment: str = Field(default="", max_length=1000)
