from decimal import ROUND_HALF_UP, Decimal
import math
from typing import Annotated, Any, Literal

from pydantic import BeforeValidator


def nan_to_none(value: Any) -> Any:
    """
    Если value — float и является NaN, вернуть None,
    иначе вернуть value без изменений.
    """
    if isinstance(value, float) and math.isnan(value):
        return None
    return value

def normalize_str(
    value: str, *,
    case: Literal["lower", "upper"] = "lower"
) -> str:
    """

    """
    s = str(value)
    s = " ".join(s.split())
    if case == "upper":
        return s.upper()
    return s.lower()


def round_decimal(v: Decimal) -> Decimal:
    """Округляет Decimal до целого числа"""
    if isinstance(v, Decimal):
        return v.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return Decimal(v).quantize(Decimal('1'), rounding=ROUND_HALF_UP)

RoundedDecimal = Annotated[Decimal, BeforeValidator(round_decimal)]
