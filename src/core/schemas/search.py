from decimal import Decimal
from typing import Annotated, Optional, Generic, TypeVar
from enum import Enum

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

T = TypeVar('T')


class FilterOperator(str, Enum):
    """Enum for filter operators"""
    CONTAINS = "contains"
    DOES_NOT_CONTAIN = "does_not_contain"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"
    IN = "in"
    NOT_IN = "not_in"


class SortDirection(str, Enum):
    """Enum for sort directions"""
    ASC = "asc"
    DESC = "desc"


class BaseFilterItem(BaseModel):
    """Base model for filter item"""
    column: str
    value: str
    operator: FilterOperator

    model_config = ConfigDict(from_attributes=True)


class BaseSortItem(BaseModel):
    """Base model for sort item"""
    column: str
    direction: Annotated[SortDirection, BeforeValidator(lambda v: v.lower() if isinstance(v, str) else v)]

    model_config = ConfigDict(from_attributes=True)


class BaseSearchRequestBody(BaseModel):
    """Base model for search request body"""
    search: Optional[str] = None
    page: Optional[int] = Field(default=1, ge=1)
    page_size: Optional[int] = Field(default=20, ge=1, le=100)
    filter: Optional[list[BaseFilterItem]] = None
    sort: Optional[list[BaseSortItem]] = None

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel, Generic[T]):
    """Generic search response with pagination metadata"""
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def create(
        cls, 
        items: list[T], 
        total: int, 
        page: int, 
        page_size: int
    ) -> "SearchResponse[T]":
        """Helper method to create search response with calculated total_pages"""
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )