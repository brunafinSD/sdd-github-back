from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import PyObjectId
from app.models.enums import CashTarget, TransactionType


class TransactionResponse(BaseModel):
    """Transaction representation in API responses."""

    id: PyObjectId = Field(alias="_id")
    type: TransactionType
    amount: int
    description: str | None = None
    justification: str | None = None
    game_id: PyObjectId | None = Field(default=None, alias="gameId")
    cash_target: CashTarget = Field(alias="cashTarget")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)


class TransactionInDB(BaseModel):
    """Transaction document shape for insertion into MongoDB."""

    type: TransactionType
    amount: int
    description: str | None = None
    justification: str | None = None
    game_id: str | None = Field(default=None, alias="gameId")
    cash_target: CashTarget = Field(alias="cashTarget")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)

    def to_doc(self) -> dict:
        """Convert to MongoDB document dict."""
        return self.model_dump(by_alias=True)


class ManualTransactionCreate(BaseModel):
    """Request body for creating a manual transaction."""

    type: TransactionType
    amount: int = Field(gt=0)
    description: str | None = None
    justification: str = Field(min_length=5, max_length=500)
    cash_target: CashTarget = Field(default=CashTarget.ADM, alias="cashTarget")

    model_config = ConfigDict(populate_by_name=True)


class TransferRequest(BaseModel):
    """Request body for a court→adm transfer."""

    amount: int = Field(gt=0)
