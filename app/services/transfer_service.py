from datetime import UTC, datetime

from bson import ObjectId
from fastapi import HTTPException, status

from app.database import get_database
from app.models.enums import CashTarget, GameStatus, TransactionType
from app.models.transaction import TransactionInDB
from app.services.cash_service import get_court_balance


async def create_transfer(amount: int) -> dict:
    """Transfer money from court balance to ADM balance.

    Creates 2 transactions:
    1. type=transfer, cashTarget=court, amount=-N
    2. type=transfer, cashTarget=adm,   amount=+N
    """
    court_balance = await get_court_balance()

    if amount > court_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Saldo insuficiente no caixa quadra",
        )

    db = get_database()
    now = datetime.now(UTC)
    description = "Transferência Quadra → ADM"

    court_txn = TransactionInDB(
        type=TransactionType.TRANSFER,
        amount=-amount,
        description=description,
        cashTarget=CashTarget.COURT,
        createdAt=now,
    )

    adm_txn = TransactionInDB(
        type=TransactionType.TRANSFER,
        amount=amount,
        description=description,
        cashTarget=CashTarget.ADM,
        createdAt=now,
    )

    court_doc = court_txn.to_doc()
    adm_doc = adm_txn.to_doc()

    result = await db.transactions.insert_many([court_doc, adm_doc])
    court_doc["_id"] = result.inserted_ids[0]
    adm_doc["_id"] = result.inserted_ids[1]

    return {
        "transferredAmount": amount,
        "courtTransaction": court_doc,
        "admTransaction": adm_doc,
    }


async def apply_credit(game_id: str, amount: int) -> dict:
    """Apply court balance as credit to a pending game.

    Sets game.courtCredit and creates a manual_out transaction on court.
    """
    from app.services.game_service import get_game

    game = await get_game(game_id)

    if game["status"] != GameStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Crédito só pode ser aplicado a jogos pendentes",
        )

    court_balance = await get_court_balance()

    if amount > court_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Saldo insuficiente no caixa quadra",
        )

    db = get_database()
    now = datetime.now(UTC)

    # Set courtCredit on the game
    await db.games.update_one(
        {"_id": ObjectId(game_id)},
        {
            "$set": {
                "courtCredit": amount,
                "updatedAt": now,
            }
        },
    )

    # Create transaction for the court debit
    txn = TransactionInDB(
        type=TransactionType.MANUAL_OUT,
        amount=-amount,
        description="Crédito de quadra aplicado ao jogo",
        cashTarget=CashTarget.COURT,
        createdAt=now,
    )
    await db.transactions.insert_one(txn.to_doc())

    return await get_game(game_id)
