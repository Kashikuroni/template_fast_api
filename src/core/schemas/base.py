from typing import Any, Optional, TypeVar, Generic, TypeAlias
from pydantic import BaseModel

T = TypeVar("T")
DataList: TypeAlias = list[dict[str, Any]]
ErrorList: TypeAlias = list[dict[str, Any]]

class BulkCreateResult(BaseModel):
    created: DataList
    errors:  ErrorList

class BulkUpdateResult(BaseModel):
    updated: DataList
    errors:  ErrorList

class ResponseSchema(BaseModel, Generic[T]):
    data: Optional[T] = []
    message: Optional[str] = ""
    errors: Optional[ErrorList] = []