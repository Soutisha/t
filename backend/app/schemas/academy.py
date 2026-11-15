from pydantic import BaseModel, Field, field_validator

class LessonInput(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(default="", max_length=20000)
    sequence: int = Field(ge=1, le=200)
    estimated_minutes: int = Field(default=5, ge=1, le=600)
    asset_type: str = Field(default="article", pattern="^(article|video|interactive_3d|ar_demo|document)$")
    asset_reference: str = Field(default="", max_length=500)
    required: bool = True

class QuestionInput(BaseModel):
    prompt: str = Field(min_length=5, max_length=2000)
    options: list[str] = Field(min_length=2, max_length=6)
    correct_option: int = Field(ge=0, le=5)
    explanation: str = Field(default="", max_length=2000)
    sequence: int = Field(ge=1, le=100)

    @field_validator("options")
    @classmethod
    def options_not_empty(cls, value):
        if any(not x.strip() or len(x) > 500 for x in value):
            raise ValueError("Each quiz option must contain 1–500 characters.")
        return value

class CourseCreate(BaseModel):
    course_code: str = Field(min_length=2, max_length=60, pattern="^[A-Za-z0-9_-]+$")
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=5000)
    category: str = Field(default="technical", max_length=60)
    difficulty: str = Field(default="beginner", pattern="^(beginner|intermediate|advanced)$")
    language: str = Field(default="en", max_length=12)
    estimated_minutes: int = Field(default=30, ge=1, le=10000)
    pass_percentage: float = Field(default=70, ge=1, le=100)
    lessons: list[LessonInput] = Field(min_length=1, max_length=100)
    questions: list[QuestionInput] = Field(min_length=1, max_length=100)

class QuizSubmission(BaseModel):
    answers: dict[str, int] = Field(min_length=1, max_length=100)
