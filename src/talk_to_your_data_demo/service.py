from __future__ import annotations

import sqlite3
import time
from typing import Any

from .catalog import compile_question, supported_questions
from .guardrails import MAX_RESULT_ROWS, install_read_only_authorizer, validate_read_only_sql
from .models import QueryResult
from .synthetic import build_demo_connection, demo_stats


class QueryTimeoutError(RuntimeError):
    """Raised when SQLite exceeds the small demo execution budget."""


class TalkToYourDataDemo:
    """Offline service: bounded questions, exact SQL visibility, read-only execution."""

    def __init__(self, *, timeout_ms: int = 500) -> None:
        if not 10 <= timeout_ms <= 5_000:
            raise ValueError("timeout_ms must be between 10 and 5000")
        self.timeout_ms = timeout_ms

    @staticmethod
    def questions() -> tuple[str, ...]:
        return supported_questions()

    @staticmethod
    def stats() -> dict[str, object]:
        connection = build_demo_connection()
        try:
            return demo_stats(connection)
        finally:
            connection.close()

    def ask(self, question: str) -> QueryResult:
        plan = compile_question(question)
        validate_read_only_sql(plan.sql)

        connection = build_demo_connection()
        started = time.perf_counter()
        deadline = started + (self.timeout_ms / 1000.0)
        try:
            source_rows = int(connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0])
            install_read_only_authorizer(connection)
            connection.set_progress_handler(lambda: int(time.perf_counter() > deadline), 1_000)
            cursor = connection.execute(plan.sql, plan.parameters)
            columns = tuple(description[0] for description in cursor.description or ())
            raw_rows = cursor.fetchmany(MAX_RESULT_ROWS + 1)
        except sqlite3.OperationalError as error:
            if "interrupted" in str(error).casefold():
                raise QueryTimeoutError("query exceeded the execution budget") from error
            raise
        finally:
            connection.close()

        rows = tuple(
            tuple(self._safe_cell(value) for value in row) for row in raw_rows[:MAX_RESULT_ROWS]
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return QueryResult(
            plan=plan,
            columns=columns,
            rows=rows,
            summary=self._summarize(plan.plan_id, columns, rows),
            synthetic_source_rows=source_rows,
            truncated=len(raw_rows) > MAX_RESULT_ROWS,
            elapsed_ms=elapsed_ms,
        )

    @staticmethod
    def _safe_cell(value: Any) -> Any:
        if value is None or isinstance(value, (int, float, str, bool)):
            return value
        return str(value)

    @staticmethod
    def _summarize(
        plan_id: str, columns: tuple[str, ...], rows: tuple[tuple[Any, ...], ...]
    ) -> str:
        if not rows:
            return "The synthetic dataset returned no matching rows."
        column_index = {name: index for index, name in enumerate(columns)}
        if plan_id == "top_products":
            first = rows[0]
            return f"{first[column_index['product_name']]} leads the synthetic dataset by revenue."
        if plan_id == "refund_rate_by_region":
            first = rows[0]
            return (
                f"{first[column_index['region']]} has the highest synthetic refund rate at "
                f"{first[column_index['refund_rate_pct']]}%."
            )
        if plan_id == "average_order_value_by_channel":
            first = rows[0]
            return (
                f"{first[column_index['channel']]} has the highest synthetic average order value "
                f"at {first[column_index['average_order_value']]} units."
            )
        if plan_id == "last_30_days":
            total_orders = sum(int(row[column_index["orders"]]) for row in rows)
            total_revenue = sum(float(row[column_index["revenue"]]) for row in rows)
            return (
                f"The final 30 synthetic days contain {total_orders} orders and "
                f"{total_revenue:.2f} revenue units."
            )
        return f"The query returned {len(rows)} bounded aggregate rows from synthetic data."
