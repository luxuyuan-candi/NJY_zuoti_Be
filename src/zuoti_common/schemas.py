from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    success: bool = True
    data: dict | list | None = None
    message: str = "ok"


class LoginByCodeRequest(BaseModel):
    code: str = Field(min_length=1)
    nickname: str | None = None
    avatar_url: str | None = None


class FeedbackRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    category: str = "general"


class AuthorizationRequest(BaseModel):
    user_id: str
    target_type: str
    target_id: str
    enabled: bool = True
