from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class QueryPlan:
    """A deterministic, allowlisted question-to-SQL plan."""

    plan_id: str
    title: str
    question: str
    sql: str
    parameters: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QueryResult:
    """Safe projection returned by the demo service."""

    plan: QueryPlan
    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    summary: str
    synthetic_source_rows: int
    truncated: bool
    elapsed_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan.to_dict(),
            "columns": list(self.columns),
            "rows": [list(row) for row in self.rows],
            "summary": self.summary,
            "synthetic_source_rows": self.synthetic_source_rows,
            "truncated": self.truncated,
            "elapsed_ms": round(self.elapsed_ms, 3),
        }
