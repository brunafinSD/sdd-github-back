from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "fut_pay_manager"
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    auth_username: str = "parceriasdojoguinho"
    auth_password: str = "futdaquinta"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
