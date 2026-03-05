from datetime import UTC, datetime, timedelta

import jwt

from app.config import settings

ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24


def validate_credentials(username: str, password: str) -> bool:
    """Validate login credentials against settings. Trims input."""
    return username.strip() == settings.auth_username and password.strip() == settings.auth_password


def create_access_token(username: str) -> str:
    """Create a JWT token with 24h expiry."""
    now = datetime.now(UTC)
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)
