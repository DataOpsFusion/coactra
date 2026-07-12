"""SQL-backed durable WorkStore.

This backend persists the complete WorkOrder snapshot as JSON plus indexed columns for
scope, status, idempotency, and optimistic-concurrency version checks. WorkManager remains
the lifecycle owner; this store owns durable, multi-process-safe persistence.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from coactra.scope import Scope
from coactra.workflow.ledger.domain.events import EventEnvelope
from coactra.workflow.ledger.domain.models import WorkOrder, WorkStatus
from coactra.workflow.ledger.store import ConflictError


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _require_sqlalchemy():
    try:
        from sqlalchemy import (
            DateTime,
            Index,
            Integer,
            MetaData,
            String,
            Table,
            Text,
            and_,
            create_engine,
            insert,
            select,
            update,
        )
        from sqlalchemy.exc import IntegrityError
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError("SqlWorkStore requires SQLAlchemy; install with coactra[sql]") from exc
    return {
        "DateTime": DateTime,
        "Index": Index,
        "Integer": Integer,
        "MetaData": MetaData,
        "String": String,
        "Table": Table,
        "Text": Text,
        "and_": and_,
        "create_engine": create_engine,
        "insert": insert,
        "select": select,
        "update": update,
        "IntegrityError": IntegrityError,
    }


class SqlWorkStore:
    """Durable SQL WorkStore for SQLite local/dev and SQLAlchemy-compatible production DBs."""

    def __init__(
        self,
        url: str = "sqlite:///:memory:",
        *,
        engine: Any | None = None,
        create: bool = True,
    ) -> None:
        self._sa = _require_sqlalchemy()
        self._metadata = self._sa["MetaData"]()
        self._orders = self._orders_table()
        self._events = self._events_table()
        if engine is None:
            kwargs: dict[str, Any] = {"future": True}
            if url.startswith("sqlite"):
                kwargs["connect_args"] = {"check_same_thread": False}
            engine = self._sa["create_engine"](url, **kwargs)
        self._engine = engine
        if create:
            self._metadata.create_all(self._engine)

    @classmethod
    def from_url(cls, url: str, **kwargs: Any) -> SqlWorkStore:
        """Construct from a SQLAlchemy URL, e.g. sqlite:///work.db or postgresql+psycopg://..."""
        return cls(url, **kwargs)

    def _orders_table(self):
        Table = self._sa["Table"]
        String = self._sa["String"]
        Integer = self._sa["Integer"]
        Text = self._sa["Text"]
        DateTime = self._sa["DateTime"]
        Index = self._sa["Index"]
        table = Table(
            "coactra_work_orders",
            self._metadata,
            self._column("id", String(255), primary_key=True),
            self._column("tenant_id", String(255), nullable=False),
            self._column("namespace", String(255), nullable=False),
            self._column("status", String(64), nullable=False),
            self._column("idempotency_key", String(255), nullable=True),
            self._column("version", Integer, nullable=False),
            self._column("order_json", Text, nullable=False),
            self._column("created_at", DateTime(timezone=True), nullable=False),
            self._column("updated_at", DateTime(timezone=True), nullable=False),
        )
        Index(
            "ix_coactra_work_orders_scope_status",
            table.c.tenant_id,
            table.c.namespace,
            table.c.status,
        )
        Index(
            "ux_coactra_work_orders_idempotency",
            table.c.tenant_id,
            table.c.namespace,
            table.c.idempotency_key,
            unique=True,
        )
        return table

    def _events_table(self):
        Table = self._sa["Table"]
        String = self._sa["String"]
        Integer = self._sa["Integer"]
        Text = self._sa["Text"]
        DateTime = self._sa["DateTime"]
        Index = self._sa["Index"]
        table = Table(
            "coactra_work_events",
            self._metadata,
            self._column("id", Integer, primary_key=True, autoincrement=True),
            self._column("tenant_id", String(255), nullable=False),
            self._column("namespace", String(255), nullable=True),
            self._column("subject", String(255), nullable=False),
            self._column("type", String(255), nullable=False),
            self._column("event_json", Text, nullable=False),
            self._column("created_at", DateTime(timezone=True), nullable=False),
        )
        Index(
            "ix_coactra_work_events_subject", table.c.tenant_id, table.c.namespace, table.c.subject
        )
        return table

    def _column(self, *args: Any, **kwargs: Any):
        from sqlalchemy import Column

        return Column(*args, **kwargs)

    def save(self, order: WorkOrder, *, expected_version: int | None = None) -> WorkOrder:
        return self._save_order(order, expected_version=expected_version)

    def save_with_event(
        self,
        order: WorkOrder,
        event: EventEnvelope,
        *,
        expected_version: int | None = None,
    ) -> WorkOrder:
        return self._save_order(order, expected_version=expected_version, event=event)

    def _save_order(
        self,
        order: WorkOrder,
        *,
        expected_version: int | None = None,
        event: EventEnvelope | None = None,
    ) -> WorkOrder:
        now = _utc_now()
        select = self._sa["select"]
        update = self._sa["update"]
        insert = self._sa["insert"]
        IntegrityError = self._sa["IntegrityError"]
        with self._engine.begin() as conn:
            current = (
                conn.execute(
                    select(
                        self._orders.c.version,
                        self._orders.c.tenant_id,
                        self._orders.c.namespace,
                        self._orders.c.created_at,
                    ).where(self._orders.c.id == order.id)
                )
                .mappings()
                .first()
            )
            if current is not None and (
                current["tenant_id"] != order.scope.tenant_id
                or current["namespace"] != order.scope.namespace
            ):
                raise ConflictError("work id already belongs to another scope")
            if expected_version is not None:
                actual = current["version"] if current is not None else 0
                if actual != expected_version:
                    raise ConflictError(
                        f"stale work order {order.id!r}: "
                        f"expected version {expected_version}, got {actual}"
                    )
            new_version = (current["version"] + 1) if current is not None else 1
            stored = order.model_copy(deep=True, update={"version": new_version})
            values = {
                "tenant_id": stored.scope.tenant_id,
                "namespace": stored.scope.namespace,
                "status": stored.status.value,
                "idempotency_key": stored.idempotency_key,
                "version": stored.version,
                "order_json": stored.model_dump_json(),
                "updated_at": now,
            }
            try:
                if current is None:
                    conn.execute(
                        insert(self._orders).values(
                            id=stored.id,
                            created_at=now,
                            **values,
                        )
                    )
                else:
                    predicate = self._orders.c.id == stored.id
                    if expected_version is not None:
                        predicate = self._sa["and_"](
                            predicate, self._orders.c.version == expected_version
                        )
                    result = conn.execute(update(self._orders).where(predicate).values(**values))
                    if expected_version is not None and result.rowcount != 1:
                        raise ConflictError(
                            f"stale work order {stored.id!r}: expected version {expected_version}"
                        )
            except IntegrityError as exc:
                raise ConflictError(
                    "work order id or idempotency key conflicts with an existing order"
                ) from exc
            if event is not None:
                self._insert_event(conn, event)
            return stored.model_copy(deep=True)

    def get(self, work_id: str, scope: Scope) -> WorkOrder | None:
        select = self._sa["select"]
        with self._engine.begin() as conn:
            row = (
                conn.execute(
                    select(self._orders.c.order_json).where(
                        self._orders.c.id == work_id,
                        self._orders.c.tenant_id == scope.tenant_id,
                        self._orders.c.namespace == scope.namespace,
                    )
                )
                .mappings()
                .first()
            )
        return self._order_from_row(row) if row is not None else None

    def find_by_idempotency_key(self, key: str, scope: Scope) -> WorkOrder | None:
        select = self._sa["select"]
        with self._engine.begin() as conn:
            row = (
                conn.execute(
                    select(self._orders.c.order_json).where(
                        self._orders.c.tenant_id == scope.tenant_id,
                        self._orders.c.namespace == scope.namespace,
                        self._orders.c.idempotency_key == key,
                    )
                )
                .mappings()
                .first()
            )
        return self._order_from_row(row) if row is not None else None

    def list(self, scope: Scope, *, status: WorkStatus | None = None) -> list[WorkOrder]:
        select = self._sa["select"]
        stmt = select(self._orders.c.order_json).where(
            self._orders.c.tenant_id == scope.tenant_id,
            self._orders.c.namespace == scope.namespace,
        )
        if status is not None:
            stmt = stmt.where(self._orders.c.status == status.value)
        stmt = stmt.order_by(self._orders.c.created_at, self._orders.c.id)
        with self._engine.begin() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [self._order_from_row(row) for row in rows]

    def append_event(self, event: EventEnvelope) -> None:
        with self._engine.begin() as conn:
            self._insert_event(conn, event)

    def _insert_event(self, conn: Any, event: EventEnvelope) -> None:
        insert = self._sa["insert"]
        namespace = event.data.get("namespace")
        if namespace is not None:
            namespace = str(namespace)
        conn.execute(
            insert(self._events).values(
                tenant_id=event.tenant_id,
                namespace=namespace,
                subject=event.subject,
                type=event.type,
                event_json=event.model_dump_json(),
                created_at=_utc_now(),
            )
        )

    def events(self, work_id: str, scope: Scope) -> list[EventEnvelope]:
        select = self._sa["select"]
        with self._engine.begin() as conn:
            rows = (
                conn.execute(
                    select(self._events.c.event_json)
                    .where(
                        self._events.c.subject == work_id,
                        self._events.c.tenant_id == scope.tenant_id,
                        self._events.c.namespace == scope.namespace,
                    )
                    .order_by(self._events.c.id)
                )
                .mappings()
                .all()
            )
        return [EventEnvelope.model_validate_json(row["event_json"]) for row in rows]

    @staticmethod
    def _order_from_row(row: Any) -> WorkOrder:
        return WorkOrder.model_validate_json(row["order_json"]).model_copy(deep=True)
