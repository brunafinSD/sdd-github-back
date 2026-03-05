from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import lifespan


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Fut Pay Manager API",
        description="API REST para gerenciamento de caixa de futsal",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Routers
    from app.auth.router import router as auth_router
    from app.routes.cash import router as cash_router
    from app.routes.games import router as games_router
    from app.routes.transactions import router as transactions_router

    app.include_router(auth_router)
    app.include_router(games_router)
    app.include_router(cash_router)
    app.include_router(transactions_router)

    return app


app = create_app()
