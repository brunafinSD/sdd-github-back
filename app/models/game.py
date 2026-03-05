from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import PyObjectId
from app.models.enums import GameStatus, PaymentMethod

# --- Player schemas ---


class PlayerCreate(BaseModel):
    """Request body for adding a player to a game."""

    name: str = Field(min_length=2, max_length=100)
    payment_method: PaymentMethod = Field(default=PaymentMethod.PIX, alias="paymentMethod")
    amount_paid: int = Field(default=1000, gt=0, alias="amountPaid")

    model_config = ConfigDict(populate_by_name=True)


class PlayerUpdate(BaseModel):
    """Request body for updating a player."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    payment_method: PaymentMethod | None = Field(default=None, alias="paymentMethod")
    amount_paid: int | None = Field(default=None, gt=0, alias="amountPaid")

    model_config = ConfigDict(populate_by_name=True)


class PlayerResponse(BaseModel):
    """Player representation in API responses."""

    id: PyObjectId
    name: str
    payment_method: PaymentMethod = Field(alias="paymentMethod")
    amount_paid: int = Field(alias="amountPaid")

    model_config = ConfigDict(populate_by_name=True)


# --- Game schemas ---


class GameCreate(BaseModel):
    """Request body for creating a game."""

    date: datetime
    court_cost: int = Field(default=9000, ge=0, alias="courtCost")

    model_config = ConfigDict(populate_by_name=True)


class GameUpdate(BaseModel):
    """Request body for updating a game."""

    date: datetime | None = None
    court_cost: int | None = Field(default=None, ge=0, alias="courtCost")

    model_config = ConfigDict(populate_by_name=True)


class GameResponse(BaseModel):
    """Game representation in API responses."""

    id: PyObjectId = Field(alias="_id")
    date: datetime
    status: GameStatus
    court_cost: int = Field(alias="courtCost")
    players: list[PlayerResponse] = []
    cash_impact: int | None = Field(default=None, alias="cashImpact")
    court_credit: int | None = Field(default=None, alias="courtCredit")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    finished_at: datetime | None = Field(default=None, alias="finishedAt")

    model_config = ConfigDict(populate_by_name=True)


class ApplyCreditRequest(BaseModel):
    """Request body for applying court credit to a game."""

    amount: int = Field(gt=0)
