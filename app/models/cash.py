from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CashSummaryResponse(BaseModel):
    """Cash summary computed from all transactions."""

    total_balance: int = Field(alias="totalBalance")
    court_balance: int = Field(alias="courtBalance")
    adm_balance: int = Field(alias="admBalance")
    total_in: int = Field(alias="totalIn")
    total_out: int = Field(alias="totalOut")
    transaction_count: int = Field(alias="transactionCount")
    last_updated_at: datetime | None = Field(default=None, alias="lastUpdatedAt")

    model_config = ConfigDict(populate_by_name=True)
