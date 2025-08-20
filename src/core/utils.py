from datetime import datetime
from typing import Optional

from pydantic import BaseModel

def to_camel(s: str) -> str:
    parts = s.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:])

def normalize(strings: str | list[str]) -> str | list[str]:
    """
    Normalizes a string or a list of strings by converting them to lowercase 
    and removing any extra whitespace.
    
    If a single string is provided, the function returns the normalized string.
    If a list of strings is provided, the function returns a list of normalized strings.
    
    Args:
        titles (Union[str, List[str]]): A string or a list of strings to normalize.
    
    Returns:
        Union[str, List[str]]: The normalized string or list of normalized strings.
    
    Raises:
        TypeError: If the input is neither a string nor a list of strings.
    """
    if isinstance(strings, str):
        return " ".join(strings.strip().split()).lower()
    elif isinstance(strings, list):
        return [" ".join(title.strip().split()).lower() for title in strings]
    else:
        raise TypeError("Expected a string or a list of strings")

def get_current_date() -> str:
    current_date = datetime.now()
    formatted_date = current_date.strftime("%d.%m.%Y")
    return formatted_date


# def export_pydantic_to_csv(
#     objects: list[BaseModel],
#     filename: str,
#     mode: str = "w",
#     encoding: str = "utf-8-sig",
#     exclude_none: bool = True,
#     exclude_fields: Optional[list[str]] = None,
# ):
#     if not objects:
#         retrun
