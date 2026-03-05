from fastapi import APIRouter, Depends

from app.auth.deps import get_current_user
from app.models.cash import CashSummaryResponse
from app.models.common import DataEnvelope
from app.services import cash_service

router = APIRouter(prefix="/cash", tags=["cash"])


@router.get("/summary", response_model=DataEnvelope[CashSummaryResponse])
async def get_cash_summary(_user: str = Depends(get_current_user)):
    """Get the current financial summary computed from all transactions."""
    summary = await cash_service.get_summary()
    return DataEnvelope(data=summary)
