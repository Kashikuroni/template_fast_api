from typing import Any, Optional
from pydantic import BaseModel

class BulkCreateResult(BaseModel):
    created: list[dict[str, Any]]
    errors:  list[dict[str, Any]] 

class BulkUpdateResult(BaseModel):
    updated: list[dict[str, Any]]
    errors:  list[dict[str, Any]] 


class ResponseSchema(BaseModel):
    data: Optional[list[dict[str, Any]]] = None
    message: Optional[str] = None
    errors: Optional[list[dict[str, Any]]] = None
