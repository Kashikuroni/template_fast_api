from datetime import datetime
from typing import Annotated, Any

from pydantic import BeforeValidator


def _prepare_iso_z(value: Any) -> str:
    if isinstance(value, str) and value.endswith("Z"):
        return value[:-1] + "+00:00"
    return value

ZDateTime = Annotated[datetime, BeforeValidator(_prepare_iso_z)]
