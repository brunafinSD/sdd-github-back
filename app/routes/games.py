from fastapi import APIRouter, Depends, Query, Response, status

from app.auth.deps import get_current_user
from app.models.common import DataEnvelope, PaginatedEnvelope, build_pagination_meta
from app.models.enums import GameStatus
from app.models.game import (
    ApplyCreditRequest,
    GameCreate,
    GameResponse,
    GameUpdate,
    PlayerCreate,
    PlayerUpdate,
)
from app.services import game_service, transfer_service

router = APIRouter(prefix="/games", tags=["games"])


@router.post(
    "",
    response_model=DataEnvelope[GameResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_game(
    body: GameCreate,
    _user: str = Depends(get_current_user),
):
    """Create a new game."""
    game = await game_service.create_game(
        date=body.date,
        court_cost=body.court_cost,
    )
    return DataEnvelope(data=GameResponse.model_validate(game))


@router.get("", response_model=PaginatedEnvelope[GameResponse])
async def list_games(
    month: str | None = Query(default=None, description="Filter by month (YYYY-MM)"),
    game_status: GameStatus | None = Query(
        default=None, alias="status", description="Filter by status"
    ),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _user: str = Depends(get_current_user),
):
    """List games with optional filters and pagination."""
    games, total = await game_service.list_games(
        month=month,
        game_status=game_status,
        page=page,
        limit=limit,
    )
    return PaginatedEnvelope(
        data=[GameResponse.model_validate(g) for g in games],
        meta=build_pagination_meta(page=page, limit=limit, total=total),
    )


@router.get("/{game_id}", response_model=DataEnvelope[GameResponse])
async def get_game(
    game_id: str,
    _user: str = Depends(get_current_user),
):
    """Get a single game."""
    game = await game_service.get_game(game_id)
    return DataEnvelope(data=GameResponse.model_validate(game))


@router.put("/{game_id}", response_model=DataEnvelope[GameResponse])
async def update_game(
    game_id: str,
    body: GameUpdate,
    _user: str = Depends(get_current_user),
):
    """Update a pending game."""
    update_data = {}
    if body.date is not None:
        update_data["date"] = body.date
    if body.court_cost is not None:
        update_data["courtCost"] = body.court_cost

    game = await game_service.update_game(game_id, update_data)
    return DataEnvelope(data=GameResponse.model_validate(game))


@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game(
    game_id: str,
    _user: str = Depends(get_current_user),
):
    """Delete a pending game."""
    await game_service.delete_game(game_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Player sub-routes ---


@router.post(
    "/{game_id}/players",
    response_model=DataEnvelope[GameResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_player(
    game_id: str,
    body: PlayerCreate,
    _user: str = Depends(get_current_user),
):
    """Add a player to a pending game."""
    game = await game_service.add_player(
        game_id=game_id,
        name=body.name,
        payment_method=body.payment_method,
        amount_paid=body.amount_paid,
    )
    return DataEnvelope(data=GameResponse.model_validate(game))


@router.put(
    "/{game_id}/players/{player_id}",
    response_model=DataEnvelope[GameResponse],
)
async def update_player(
    game_id: str,
    player_id: str,
    body: PlayerUpdate,
    _user: str = Depends(get_current_user),
):
    """Update a player in a pending game."""
    update_data = {}
    if body.name is not None:
        update_data["name"] = body.name.strip()
    if body.payment_method is not None:
        update_data["paymentMethod"] = body.payment_method
    if body.amount_paid is not None:
        update_data["amountPaid"] = body.amount_paid

    game = await game_service.update_player(game_id, player_id, update_data)
    return DataEnvelope(data=GameResponse.model_validate(game))


@router.delete(
    "/{game_id}/players/{player_id}",
    response_model=DataEnvelope[GameResponse],
)
async def remove_player(
    game_id: str,
    player_id: str,
    _user: str = Depends(get_current_user),
):
    """Remove a player from a pending game."""
    game = await game_service.remove_player(game_id, player_id)
    return DataEnvelope(data=GameResponse.model_validate(game))


# --- Finalize / Cancel ---


@router.post(
    "/{game_id}/finalize",
    response_model=DataEnvelope[GameResponse],
)
async def finalize_game(
    game_id: str,
    _user: str = Depends(get_current_user),
):
    """Finalize a pending game — creates transactions and calculates cashImpact."""
    game = await game_service.finalize_game(game_id)
    return DataEnvelope(data=GameResponse.model_validate(game))


@router.post(
    "/{game_id}/cancel",
    response_model=DataEnvelope[GameResponse],
)
async def cancel_game(
    game_id: str,
    _user: str = Depends(get_current_user),
):
    """Cancel a pending game."""
    game = await game_service.cancel_game(game_id)
    return DataEnvelope(data=GameResponse.model_validate(game))


# --- Apply credit ---


@router.post(
    "/{game_id}/apply-credit",
    response_model=DataEnvelope[GameResponse],
)
async def apply_credit(
    game_id: str,
    body: ApplyCreditRequest,
    _user: str = Depends(get_current_user),
):
    """Apply court balance as credit to reduce a game's effective court cost."""
    game = await transfer_service.apply_credit(game_id, body.amount)
    return DataEnvelope(data=GameResponse.model_validate(game))
