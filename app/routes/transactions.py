from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.deps import get_current_user
from app.models.common import DataEnvelope, PaginatedEnvelope, build_pagination_meta
from app.models.enums import CashTarget, TransactionType
from app.models.transaction import ManualTransactionCreate, TransactionResponse, TransferRequest
from app.services import cash_service, transfer_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post(
    "",
    response_model=DataEnvelope[TransactionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_manual_transaction(
    body: ManualTransactionCreate,
    _user: str = Depends(get_current_user),
):
    """Create a manual transaction (manual_in or manual_out only)."""
    # Validate only manual types allowed
    if body.type not in (TransactionType.MANUAL_IN, TransactionType.MANUAL_OUT):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Apenas transações manuais (manual_in, manual_out) são permitidas",
        )

    txn = await cash_service.create_manual_transaction(
        txn_type=body.type,
        amount=body.amount,
        description=body.description,
        justification=body.justification,
        cash_target=body.cash_target,
    )
    return DataEnvelope(data=TransactionResponse.model_validate(txn))


@router.get("", response_model=PaginatedEnvelope[TransactionResponse])
async def list_transactions(
    date_from: str | None = Query(
        default=None, alias="from", description="Start date (YYYY-MM-DD)"
    ),
    date_to: str | None = Query(default=None, alias="to", description="End date (YYYY-MM-DD)"),
    txn_type: TransactionType | None = Query(default=None, alias="type"),
    cash_target: CashTarget | None = Query(default=None, alias="cashTarget"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    _user: str = Depends(get_current_user),
):
    """List transactions with optional filters and pagination."""
    transactions, total = await cash_service.list_transactions(
        date_from=date_from,
        date_to=date_to,
        txn_type=txn_type,
        cash_target=cash_target,
        page=page,
        limit=limit,
    )
    return PaginatedEnvelope(
        data=[TransactionResponse.model_validate(t) for t in transactions],
        meta=build_pagination_meta(page=page, limit=limit, total=total),
    )


@router.post(
    "/transfer",
    response_model=DataEnvelope[dict],
    status_code=status.HTTP_201_CREATED,
)
async def create_transfer(
    body: TransferRequest,
    _user: str = Depends(get_current_user),
):
    """Transfer money from court balance to ADM balance."""
    result = await transfer_service.create_transfer(body.amount)

    # Format response with TransactionResponse for each sub-transaction
    return DataEnvelope(
        data={
            "transferredAmount": result["transferredAmount"],
            "courtTransaction": TransactionResponse.model_validate(
                result["courtTransaction"]
            ).model_dump(by_alias=True),
            "admTransaction": TransactionResponse.model_validate(
                result["admTransaction"]
            ).model_dump(by_alias=True),
        }
    )
