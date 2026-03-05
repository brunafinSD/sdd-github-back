from datetime import UTC, datetime

from app.database import get_database
from app.models.cash import CashSummaryResponse
from app.models.enums import CashTarget, TransactionType
from app.models.transaction import TransactionInDB


async def get_summary() -> CashSummaryResponse:
    """Compute the cash summary from all transactions via aggregation pipeline."""
    db = get_database()

    pipeline = [
        {
            "$group": {
                "_id": None,
                "totalIn": {"$sum": {"$cond": [{"$gt": ["$amount", 0]}, "$amount", 0]}},
                "totalOut": {"$sum": {"$cond": [{"$lt": ["$amount", 0]}, {"$abs": "$amount"}, 0]}},
                "courtBalance": {
                    "$sum": {"$cond": [{"$eq": ["$cashTarget", "court"]}, "$amount", 0]}
                },
                "admBalance": {"$sum": {"$cond": [{"$eq": ["$cashTarget", "adm"]}, "$amount", 0]}},
                "transactionCount": {"$sum": 1},
                "lastUpdatedAt": {"$max": "$createdAt"},
            }
        }
    ]

    cursor = db.transactions.aggregate(pipeline)
    results = await cursor.to_list(length=1)

    if not results:
        return CashSummaryResponse(
            totalBalance=0,
            courtBalance=0,
            admBalance=0,
            totalIn=0,
            totalOut=0,
            transactionCount=0,
            lastUpdatedAt=None,
        )

    result = results[0]
    court = result["courtBalance"]
    adm = result["admBalance"]

    return CashSummaryResponse(
        totalBalance=court + adm,
        courtBalance=court,
        admBalance=adm,
        totalIn=result["totalIn"],
        totalOut=result["totalOut"],
        transactionCount=result["transactionCount"],
        lastUpdatedAt=result["lastUpdatedAt"],
    )


async def get_court_balance() -> int:
    """Get just the court balance — used by transfer and apply-credit validations."""
    summary = await get_summary()
    return summary.court_balance


async def create_manual_transaction(
    *,
    txn_type: TransactionType,
    amount: int,
    description: str | None,
    justification: str,
    cash_target: CashTarget,
) -> dict:
    """Create a manual transaction (manual_in or manual_out)."""
    db = get_database()
    now = datetime.now(UTC)

    # For manual_out, negate the amount
    stored_amount = amount if txn_type == TransactionType.MANUAL_IN else -amount

    txn = TransactionInDB(
        type=txn_type,
        amount=stored_amount,
        description=description,
        justification=justification,
        gameId=None,
        cashTarget=cash_target,
        createdAt=now,
    )

    doc = txn.to_doc()
    result = await db.transactions.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def list_transactions(
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    txn_type: TransactionType | None = None,
    cash_target: CashTarget | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[dict], int]:
    """List transactions with optional filters and pagination."""
    db = get_database()
    query: dict = {}

    if txn_type:
        query["type"] = txn_type

    if cash_target:
        query["cashTarget"] = cash_target

    # Date range filter on createdAt
    date_filter: dict = {}
    if date_from:
        try:
            start = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=UTC)
            date_filter["$gte"] = start
        except ValueError:
            pass
    if date_to:
        try:
            # End of day (inclusive)
            end = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=UTC)
            end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
            date_filter["$lte"] = end
        except ValueError:
            pass
    if date_filter:
        query["createdAt"] = date_filter

    skip = (page - 1) * limit
    total = await db.transactions.count_documents(query)
    cursor = db.transactions.find(query).sort("createdAt", -1).skip(skip).limit(limit)
    transactions = await cursor.to_list(length=limit)

    return transactions, total
