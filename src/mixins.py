from typing import ClassVar, Optional


class RelationMixin:
    """
    Базовый Миксин который говорит что у всех наследников
    должно быть поле `__back_populates__`
    """
    __back_populates__: ClassVar[Optional[str]] = None
