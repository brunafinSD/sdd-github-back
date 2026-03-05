from math import ceil
from typing import Annotated, Generic, TypeVar

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, Field

T = TypeVar("T")

PyObjectId = Annotated[str, BeforeValidator(str)]


class DataEnvelope(BaseModel, Generic[T]):
    """Generic response wrapper: { "data": <T> }"""

    data: T


class PaginationMeta(BaseModel):
    """Pagination metadata for list endpoints."""

    page: int = Field(ge=1)
    limit: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0, alias="totalPages")

    model_config = {"populate_by_name": True}


class PaginatedEnvelope(BaseModel, Generic[T]):
    """Paginated response wrapper: { "data": [...], "meta": { ... } }"""

    data: list[T]
    meta: PaginationMeta


def build_pagination_meta(*, page: int, limit: int, total: int) -> PaginationMeta:
    """Create PaginationMeta from counts."""
    return PaginationMeta(
        page=page,
        limit=limit,
        total=total,
        totalPages=ceil(total / limit) if limit > 0 else 0,
    )


def validate_object_id(value: str) -> str:
    """Validate that a string is a valid MongoDB ObjectId format."""
    if not ObjectId.is_valid(value):
        raise ValueError("ID inválido")
    return value
