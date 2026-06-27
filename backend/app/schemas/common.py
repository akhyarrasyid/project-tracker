"""Generic paginated response wrapper."""
from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard envelope for paginated list endpoints."""

    items: List[T]
    total: int
    page: int
    size: int
    pages: int
