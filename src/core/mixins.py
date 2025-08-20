"""Reusable bulk‑update helper for SQLAlchemy 2 async repositories (PostgreSQL‑only).

This snippet is meant to live inside (or be imported by) your ``BaseCRUDRepository``.  It
assumes the repository already keeps a reference to ``self.db_session`` (an
``AsyncSession``) and to ``self.model`` (a declarative model whose primary key is the
integer ``id`` column).  The repository constructor also takes ``workspace_id`` and the
respective column exists on most tables; if the current model *does not* have that
column, the filter is silently skipped.

The implementation relies on the PostgreSQL‑specific
``UPDATE … SET … FROM (VALUES …) AS d(id, col1, col2 …)`` pattern: one statement per
batch, each row may carry its own set of new values.  Compared with row‑by‑row updates
this yields a ~20–50× speed‑up on typical workloads while keeping the code entirely in
Python (no server‑side functions required).

Key features
------------
* **Schema‑driven input** – accepts any *pydantic v2* model; partial objects supported.
* **Explicit or implicit fields** – caller may pass ``update_fields`` or leave it
  ``None`` to update *all* fields present in each object (excluding ``id``).
* **Batch splitter** – honours the same ``_MAX_QUERY_PARAMS`` rule as ``bulk_create``.
* **Workspace isolation** – when the target table has ``workspace_id`` column its value
  is checked automatically; rows from other workspaces are treated as errors.
* **Selective ``None`` behaviour** – ``include_none`` decides whether ``None`` values
  overwrite DB values or are ignored.
* **Error capture** – collects *id* and error message for rows that were not updated
  (missing id, workspace mismatch, constraint violation, etc.).
* **Commit inside** – commits after every successful batch as requested.

Limitations / assumptions
-------------------------
* Single‑column integer primary key named ``id``.
* PostgreSQL ≥ 9.5 (``UPDATE … FROM`` + ``VALUES`` is available since 9.4).
* No attempt to fall back to portable SQL.  If you ever switch DBs you need another
  strategy.
* All objects in one batch must share the same set of columns – the helper groups
  rows accordingly when ``update_fields`` is ``None`` so you do not need to care.
"""

from collections import defaultdict
from itertools import batched
from typing import Any, Iterable, Sequence, TypeVar

from loguru import logger
import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

_MAX_QUERY_PARAMS = 20_000
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


class BulkUpdateResult(BaseModel):
    """Return value of :meth:`bulk_update`."""
    updated: list[dict[str, Any]]
    errors: list[dict[str, Any]]


class BulkUpdateMixin:
    """Add this mixin to your BaseCRUDRepository to get ``bulk_update``."""

    db_session: AsyncSession  # filled by parent class
    workspace_id: int
    model: type  # declarative model with ``__table__``

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────
    async def bulk_update(
        self,
        payload: Sequence[UpdateSchemaT],
        update_fields: Sequence[str] | None = None,
        *,
        include_none: bool = False,
    ) -> BulkUpdateResult:
        """Mass‑update rows by primary key.

        Parameters
        ----------
        payload:
            Sequence of *pydantic* objects whose **``id``** attribute points at existing
            rows.
        update_fields:
            Iterable with column names to update, or ``None`` to update *every* field
            that is present (and not ``None``) in the respective schema instance.
        include_none:
            When *False* (default) ``None`` values are **ignored** (the column is left
            untouched).  When *True* ``None`` explicitly overwrites the DB value.

        Returns
        -------
        BulkUpdateResult
            ``updated`` – list with *id* and new column values per successfully
            modified row.
            ``errors`` – list with *id* and string describing the failure cause.
        """

        if not payload:
            return BulkUpdateResult(updated=[], errors=[])

        table = self.model.__table__
        workspace_filter = (
            table.c.workspace_id == sa.bindparam("workspace_id")
            if "workspace_id" in table.c
            else None
        )

        # 1. Normalise rows → dict[ column -> value ]
        normalised: list[dict[str, Any]] = []
        for item in payload:
            # Exclude id – we handle it separately
            raw: dict[str, Any] = item.model_dump(exclude_none=False)
            if "id" not in raw:
                raise ValueError("Every update schema must include an 'id' field")
            row: dict[str, Any] = {"id": raw["id"]}

            if update_fields is None:
                cand = {
                    k: v
                    for k, v in raw.items()
                    if k != "id" and (v is not None or include_none)
                }
            else:
                cand = {
                    k: raw.get(k)
                    for k in update_fields
                    if (raw.get(k) is not None or include_none)
                }

            if not cand:
                # Nothing to update – treat as error and continue
                normalised.append(row | {"__empty": True})
            else:
                row.update(cand)
                normalised.append(row)

        # 2. Group by column set so that each batch shares the same VALUES signature
        groups: dict[frozenset[str], list[dict[str, Any]]] = defaultdict(list)
        for row in normalised:
            cols = frozenset(k for k in row.keys() if k not in ("id", "__empty"))
            if not cols:  # skip rows that have nothing to update
                continue
            groups[cols].append(row)

        updated: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for cols_set, rows in groups.items():
            cols = sorted(cols_set)  # stable order for param names
            num_columns = 1 + len(cols)  # id + each update column
            max_rows = _MAX_QUERY_PARAMS // num_columns or 1

            for batch_tuple in batched(rows, max_rows):
                batch: list[dict[str, Any]] = list(batch_tuple)
                if not batch:
                    continue
                try:
                    batch_result, missing_ids = await self._execute_batch_update(
                        table,
                        batch,
                        cols,
                        workspace_filter,
                        include_none=include_none,
                    )
                except IntegrityError as exc:
                    await self.db_session.rollback()
                    row_results, row_errors = (
                        await self._fallback_row_by_row(
                            table,
                            batch,
                            cols,
                            workspace_filter,
                            include_none,
                        )
                    )
                    updated.extend(row_results)
                    errors.extend(row_errors)
                    continue

                updated.extend(batch_result)
                errors.extend(
                    {"id": _id, "error": "row not found or workspace mismatch"}
                    for _id in missing_ids
                )

                await self.db_session.commit()

        for row in normalised:
            if row.get("__empty"):
                errors.append({"id": row["id"], "error": "no fields to update"})

        result = BulkUpdateResult(updated=updated, errors=errors) 
        logger.info(result)
        return result

    # ────────────────────────────────────────────────────────────────────────
    # Internals
    # ────────────────────────────────────────────────────────────────────────

    async def _execute_batch_update(
        self,
        table: sa.Table,
        batch: list[dict[str, Any]],
        cols: Sequence[str],
        workspace_filter: sa.ColumnExpressionArgument[bool] | None,
        *,
        include_none: bool,
    ) -> tuple[list[dict[str, Any]], set[int]]:
        """Generate and run one ``UPDATE … FROM (VALUES …)`` statement."""
        values_sql_parts: list[str] = []
        params: dict[str, Any] = {}
        # Pre‑compute Postgres type names to avoid repeated compilation
        from sqlalchemy.dialects import postgresql  # local import to keep deps minimal
        pg_dialect = postgresql.dialect()

        def pg_type(col_name: str) -> str:
            return table.c[col_name].type.compile(dialect=pg_dialect)

        for row_idx, row in enumerate(batch):
            placeholders = []
            # id – always bigint/int8 in our schema
            pid = f"id_{row_idx}"
            params[pid] = row["id"]
            placeholders.append(f":{pid}::{pg_type('id')}")
            # dynamic business columns
            for col in cols:
                p = f"{col}_{row_idx}"
                params[p] = row.get(col)
                placeholders.append(f":{p}::{pg_type(col)}")
            values_sql_parts.append(f"({', '.join(placeholders)})")

        values_clause = ", ".join(values_sql_parts)
        col_list = ", ".join(["id", *cols])
        set_clause = ", ".join(f"{c} = d.{c}" for c in cols)
        returning_clause = ", ".join(["t.id", *(f"t.{c}" for c in cols)])

        where_parts = ["t.id = d.id"]
        if workspace_filter is not None:
            where_parts.append("t.workspace_id = :workspace_id")
            params["workspace_id"] = self.workspace_id
        where_sql = " AND ".join(where_parts)

        sql = sa.text(
            f"""
            UPDATE {table.fullname} AS t
            SET {set_clause}
            FROM (VALUES {values_clause}) AS d({col_list})
            WHERE {where_sql}
            RETURNING {returning_clause}
            """
        )

        result = await self.db_session.execute(sql, params)
        rows = [dict(row) for row in result.mappings()]
        updated_ids = {r["id"] for r in rows}
        sent_ids = {row["id"] for row in batch}
        missing_ids = sent_ids - updated_ids
        return rows, missing_ids

    async def _fallback_row_by_row(
        self,
        table: sa.Table,
        rows: list[dict[str, Any]],
        cols: Sequence[str],
        workspace_filter: sa.ColumnExpressionArgument[bool] | None,
        include_none: bool,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Slower but isolates failing ids after a batched IntegrityError."""
        updated, errors = [], []
        for row in rows:
            stmt = (
                sa.update(table)
                .where(table.c.id == row["id"])
                .values({c: row.get(c) for c in cols})
                .returning(table.c.id, *[table.c[c] for c in cols])
            )
            if workspace_filter is not None:
                stmt = stmt.where(workspace_filter)
            try:
                res = await self.db_session.execute(stmt, {"workspace_id": self.workspace_id})
                out = res.mappings().first()
                if out:
                    updated.append(dict(out))
                    await self.db_session.commit()
                else:
                    errors.append({"id": row["id"], "error": "row not found or workspace mismatch"})
            except IntegrityError as exc:
                await self.db_session.rollback()
                errors.append({"id": row["id"], "error": str(exc)})
        return updated, errors
