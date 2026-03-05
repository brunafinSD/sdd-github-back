from fastapi import APIRouter, HTTPException, status

from app.auth.service import create_access_token, validate_credentials
from app.models.auth import LoginRequest, LoginResponse
from app.models.common import DataEnvelope

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=DataEnvelope[LoginResponse])
async def login(body: LoginRequest):
    """Authenticate and return a JWT token."""
    if not validate_credentials(body.username, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha inválidos",
        )

    token = create_access_token(body.username.strip())
    return DataEnvelope(data=LoginResponse(access_token=token))
