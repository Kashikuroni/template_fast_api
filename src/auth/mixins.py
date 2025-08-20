from typing import TYPE_CHECKING, ClassVar
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship, declared_attr

from src.mixins import RelationMixin

if TYPE_CHECKING:
    from src.auth.models import Workspace


class WorkspaceMixin(RelationMixin):
    """
    Workspace mixin.

    Defaults:
    `__workspace_with_backref__: ClassVar[bool] = True`
    `__workspace_uselist__:      ClassVar[bool] = False`
    `__workspace_parent_pk__:    ClassVar[bool] = False`


    Parameters:
    - `__workspace_with_backref__: bool`
        Whether to create the reciprocal field in Workspace.

    - `__workspace_uselist__: bool`
        `FALSE` - for One-to-One,  
        `TRUE`  - for One-to-Many.

    - `__workspace_parent_pk__: bool`
        `TRUE`  - to make the FK column the primary key.

    Note:
        Child classes `**must**` declare `__tablename__`,  
        otherwise a RuntimeError will be raised.

    """
    __workspace_backref_name__:   ClassVar[str | None] = None
    __workspace_back_populates__: ClassVar[str | None] = None
    __workspace_uselist__:        ClassVar[bool] = False
    __workspace_parent_pk__:      ClassVar[bool] = False

    @declared_attr
    def workspace_id(cls) -> Mapped[int]:
        return mapped_column(
            ForeignKey("auth.workspace.id", ondelete="CASCADE"),
            primary_key=cls.__workspace_parent_pk__,
            nullable=(not cls.__workspace_parent_pk__),
        )

    @declared_attr
    def workspace(cls) -> Mapped["Workspace"]:
        if cls.__workspace_back_populates__:
            return relationship(
                "Workspace",
                back_populates=cls.__workspace_back_populates__,
                lazy="select",
                cascade="none",
                passive_deletes=True,
            )
        elif cls.__workspace_backref_name__:
            return relationship(
                "Workspace",
                backref=cls.__workspace_backref_name__,
                lazy="select", 
                cascade="none",
                passive_deletes=True,
            )
        else:
            return relationship(
                "Workspace",
                lazy="select",
                cascade="none", 
                passive_deletes=True,
            )
