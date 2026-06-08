from pydantic import BaseModel, Field


class ApiResponse(BaseModel):
    success: bool = True
    data: dict | list | None = None
    message: str = "ok"


class LoginByCodeRequest(BaseModel):
    code: str = Field(min_length=1)
    nickname: str | None = None
    avatar_url: str | None = None


class UpdateUserProfileRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=128)
    email: str | None = Field(default=None, max_length=255)
    avatar_base64: str | None = None
    avatar_content_type: str | None = "image/jpeg"
    avatar_ext: str | None = "jpg"
    avatar_url: str | None = None


class FeedbackRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    category: str = "general"


class AuthorizationRequest(BaseModel):
    user_id: str
    target_type: str
    target_id: str
    enabled: bool = True
