from __future__ import annotations

import re
import sqlite3

MAX_SQL_BYTES = 8_000
MAX_RESULT_ROWS = 200
ALLOWED_TABLES = frozenset({"orders", "products"})

_BLOCKED_KEYWORDS = frozenset(
    {
        "alter",
        "attach",
        "create",
        "delete",
        "detach",
        "drop",
        "insert",
        "load_extension",
        "merge",
        "pragma",
        "replace",
        "transaction",
        "truncate",
        "update",
        "vacuum",
    }
)


class QueryPolicyError(ValueError):
    """Raised when SQL violates the public demo's read-only contract."""


def validate_read_only_sql(sql: str) -> None:
    if not isinstance(sql, str) or not sql.strip():
        raise QueryPolicyError("SQL must be a non-empty string")
    if len(sql.encode("utf-8")) > MAX_SQL_BYTES:
        raise QueryPolicyError("SQL exceeds the size budget")

    lowered = sql.casefold()
    if "--" in lowered or "/*" in lowered or "*/" in lowered:
        raise QueryPolicyError("SQL comments are not allowed")
    if ";" in lowered:
        raise QueryPolicyError("multiple statements are not allowed")
    if not re.match(r"^\s*(select|with)\b", lowered):
        raise QueryPolicyError("only SELECT or CTE queries are allowed")
    if re.search(r"\bselect\s+\*", lowered):
        raise QueryPolicyError("SELECT * is not allowed")

    tokens = set(re.findall(r"\b[a-z_][a-z0-9_]*\b", lowered))
    blocked = sorted(tokens & _BLOCKED_KEYWORDS)
    if blocked:
        raise QueryPolicyError(f"blocked SQL keyword: {blocked[0]}")

    cte_names = set(re.findall(r"(?:\bwith\b|,)\s*([a-z_][a-z0-9_]*)\s+as\s*\(", lowered))
    table_names = {
        name.rsplit(".", 1)[-1]
        for name in re.findall(r"\b(?:from|join)\s+([a-z_][a-z0-9_.]*)", lowered)
    }
    unexpected = sorted(table_names - ALLOWED_TABLES - cte_names)
    if unexpected:
        raise QueryPolicyError(f"table is outside the allowlist: {unexpected[0]}")

    limits = [int(value) for value in re.findall(r"\blimit\s+(\d+)\b", lowered)]
    if len(limits) != 1 or not 1 <= limits[0] <= MAX_RESULT_ROWS:
        raise QueryPolicyError(f"SQL must include one LIMIT between 1 and {MAX_RESULT_ROWS}")


def install_read_only_authorizer(connection: sqlite3.Connection) -> None:
    denied_actions = {
        sqlite3.SQLITE_ALTER_TABLE,
        sqlite3.SQLITE_ATTACH,
        sqlite3.SQLITE_CREATE_INDEX,
        sqlite3.SQLITE_CREATE_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_INDEX,
        sqlite3.SQLITE_CREATE_TEMP_TABLE,
        sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
        sqlite3.SQLITE_CREATE_TEMP_VIEW,
        sqlite3.SQLITE_CREATE_TRIGGER,
        sqlite3.SQLITE_CREATE_VIEW,
        sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_DETACH,
        sqlite3.SQLITE_DROP_INDEX,
        sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_DROP_TEMP_INDEX,
        sqlite3.SQLITE_DROP_TEMP_TABLE,
        sqlite3.SQLITE_DROP_TEMP_TRIGGER,
        sqlite3.SQLITE_DROP_TEMP_VIEW,
        sqlite3.SQLITE_DROP_TRIGGER,
        sqlite3.SQLITE_DROP_VIEW,
        sqlite3.SQLITE_INSERT,
        sqlite3.SQLITE_PRAGMA,
        sqlite3.SQLITE_REINDEX,
        sqlite3.SQLITE_TRANSACTION,
        sqlite3.SQLITE_UPDATE,
    }

    def authorize(
        action: int,
        _arg1: str | None,
        _arg2: str | None,
        _db: str | None,
        _source: str | None,
    ) -> int:
        return sqlite3.SQLITE_DENY if action in denied_actions else sqlite3.SQLITE_OK

    connection.set_authorizer(authorize)
