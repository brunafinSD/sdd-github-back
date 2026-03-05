from datetime import UTC, datetime

from bson import ObjectId
from fastapi import HTTPException, status

from app.database import get_database
from app.models.enums import CashTarget, GameStatus, PaymentMethod, TransactionType
from app.models.transaction import TransactionInDB


async def create_game(date: datetime, court_cost: int = 9000) -> dict:
    """Create a new game with pending status."""
    db = get_database()
    now = datetime.now(UTC)
    doc = {
        "date": date,
        "status": GameStatus.PENDING,
        "courtCost": court_cost,
        "players": [],
        "cashImpact": None,
        "courtCredit": None,
        "createdAt": now,
        "updatedAt": now,
        "finishedAt": None,
    }
    result = await db.games.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_game(game_id: str) -> dict:
    """Get a game by ID. Raises 404 if not found."""
    db = get_database()
    if not ObjectId.is_valid(game_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jogo não encontrado")

    game = await db.games.find_one({"_id": ObjectId(game_id)})
    if game is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jogo não encontrado")
    return game


async def list_games(
    *,
    month: str | None = None,
    game_status: GameStatus | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """List games with optional filters. Returns (games, total_count)."""
    db = get_database()
    query: dict = {}

    if game_status:
        query["status"] = game_status

    if month:
        # month format: YYYY-MM
        try:
            year, mon = month.split("-")
            start = datetime(int(year), int(mon), 1, tzinfo=UTC)
            if int(mon) == 12:
                end = datetime(int(year) + 1, 1, 1, tzinfo=UTC)
            else:
                end = datetime(int(year), int(mon) + 1, 1, tzinfo=UTC)
            query["date"] = {"$gte": start, "$lt": end}
        except (ValueError, IndexError):
            pass  # Invalid month format — ignore filter

    skip = (page - 1) * limit
    total = await db.games.count_documents(query)
    cursor = db.games.find(query).sort("date", -1).skip(skip).limit(limit)
    games = await cursor.to_list(length=limit)

    return games, total


async def update_game(game_id: str, update_data: dict) -> dict:
    """Update a pending game. Raises 400 if not pending, 404 if not found."""
    game = await get_game(game_id)

    if game["status"] != GameStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jogo não pode ser editado após finalização ou cancelamento",
        )

    db = get_database()
    # Remove None values
    fields = {k: v for k, v in update_data.items() if v is not None}
    if not fields:
        return game

    fields["updatedAt"] = datetime.now(UTC)
    await db.games.update_one({"_id": ObjectId(game_id)}, {"$set": fields})
    return await get_game(game_id)


async def delete_game(game_id: str) -> None:
    """Delete a pending game. Raises 400 if not pending, 404 if not found."""
    game = await get_game(game_id)

    if game["status"] != GameStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas jogos pendentes podem ser excluídos",
        )

    db = get_database()
    await db.games.delete_one({"_id": ObjectId(game_id)})


# --- Player management ---


async def add_player(
    game_id: str, name: str, payment_method: PaymentMethod, amount_paid: int
) -> dict:
    """Add a player to a pending game. Returns updated game."""
    game = await get_game(game_id)

    if game["status"] != GameStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jogadoras só podem ser adicionadas a jogos pendentes",
        )

    db = get_database()
    player = {
        "id": str(ObjectId()),
        "name": name.strip(),
        "paymentMethod": payment_method,
        "amountPaid": amount_paid,
    }

    await db.games.update_one(
        {"_id": ObjectId(game_id)},
        {
            "$push": {"players": player},
            "$set": {"updatedAt": datetime.now(UTC)},
        },
    )
    return await get_game(game_id)


async def update_player(game_id: str, player_id: str, update_data: dict) -> dict:
    """Update a player in a pending game. Returns updated game."""
    game = await get_game(game_id)

    if game["status"] != GameStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jogadoras não podem ser editadas em jogos finalizados ou cancelados",
        )

    # Find the player
    player_found = False
    for player in game["players"]:
        if player["id"] == player_id:
            player_found = True
            break

    if not player_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jogadora não encontrada",
        )

    db = get_database()
    set_fields: dict = {"updatedAt": datetime.now(UTC)}
    for key, value in update_data.items():
        if value is not None:
            set_fields[f"players.$.{key}"] = value

    if len(set_fields) > 1:  # more than just updatedAt
        await db.games.update_one(
            {"_id": ObjectId(game_id), "players.id": player_id},
            {"$set": set_fields},
        )

    return await get_game(game_id)


async def remove_player(game_id: str, player_id: str) -> dict:
    """Remove a player from a pending game. Returns updated game."""
    game = await get_game(game_id)

    if game["status"] != GameStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jogadoras não podem ser removidas de jogos finalizados ou cancelados",
        )

    player_found = any(p["id"] == player_id for p in game["players"])
    if not player_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jogadora não encontrada",
        )

    db = get_database()
    await db.games.update_one(
        {"_id": ObjectId(game_id)},
        {
            "$pull": {"players": {"id": player_id}},
            "$set": {"updatedAt": datetime.now(UTC)},
        },
    )
    return await get_game(game_id)


# --- Finalize / Cancel ---


async def finalize_game(game_id: str) -> dict:
    """Finalize a pending game — create transactions and calculate cashImpact."""
    game = await get_game(game_id)

    if game["status"] != GameStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jogo não pode ser finalizado",
        )

    if not game["players"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jogo sem jogadoras não pode ser finalizado",
        )

    db = get_database()
    now = datetime.now(UTC)

    # Group players by payment method and sum amounts
    pix_total = 0
    court_total = 0
    for player in game["players"]:
        if player["paymentMethod"] == PaymentMethod.PIX:
            pix_total += player["amountPaid"]
        elif player["paymentMethod"] == PaymentMethod.ON_COURT:
            court_total += player["amountPaid"]

    # Create transactions (skip zero-amount)
    transactions_to_insert = []
    game_date_str = game["date"].strftime("%d/%m/%Y")

    if pix_total > 0:
        txn = TransactionInDB(
            type=TransactionType.GAME,
            amount=pix_total,
            description=f"Jogo {game_date_str} — pagamentos pix",
            gameId=game_id,
            cashTarget=CashTarget.ADM,
            createdAt=now,
        )
        transactions_to_insert.append(txn.to_doc())

    if court_total > 0:
        txn = TransactionInDB(
            type=TransactionType.GAME,
            amount=court_total,
            description=f"Jogo {game_date_str} — pagamentos na quadra",
            gameId=game_id,
            cashTarget=CashTarget.COURT,
            createdAt=now,
        )
        transactions_to_insert.append(txn.to_doc())

    if transactions_to_insert:
        await db.transactions.insert_many(transactions_to_insert)

    # Calculate cashImpact: Σ(amountPaid) − courtCost + courtCredit
    total_paid = sum(p["amountPaid"] for p in game["players"])
    court_credit = game.get("courtCredit") or 0
    cash_impact = total_paid - game["courtCost"] + court_credit

    await db.games.update_one(
        {"_id": ObjectId(game_id)},
        {
            "$set": {
                "status": GameStatus.FINISHED,
                "cashImpact": cash_impact,
                "finishedAt": now,
                "updatedAt": now,
            }
        },
    )

    return await get_game(game_id)


async def cancel_game(game_id: str) -> dict:
    """Cancel a pending game without financial impact."""
    game = await get_game(game_id)

    if game["status"] != GameStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas jogos pendentes podem ser cancelados",
        )

    db = get_database()
    now = datetime.now(UTC)
    await db.games.update_one(
        {"_id": ObjectId(game_id)},
        {
            "$set": {
                "status": GameStatus.CANCELLED,
                "updatedAt": now,
            }
        },
    )

    return await get_game(game_id)
