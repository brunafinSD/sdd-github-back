from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Login request body."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Login success response."""

    access_token: str
    token_type: str = "bearer"
