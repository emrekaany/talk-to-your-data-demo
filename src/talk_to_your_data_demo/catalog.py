from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .models import QueryPlan
from .synthetic import DEMO_AS_OF_DATE


class UnsupportedQuestionError(ValueError):
    """Raised when a question is outside the intentionally small demo catalog."""


@dataclass(frozen=True)
class _Template:
    plan_id: str
    title: str
    examples: tuple[str, ...]
    keyword_groups: tuple[tuple[str, ...], ...]
    sql: str
    rationale: str


_TEMPLATES = (
    _Template(
        plan_id="monthly_revenue_by_region",
        title="Monthly revenue by region",
        examples=("Show monthly revenue by region", "Bölgelere göre aylık geliri göster"),
        keyword_groups=(("monthly", "aylik"), ("region", "bolge"), ("revenue", "gelir", "ciro")),
        sql="""
            SELECT
                substr(order_date, 1, 7) AS month,
                region,
                ROUND(SUM(gross_revenue), 2) AS revenue
            FROM orders
            GROUP BY substr(order_date, 1, 7), region
            ORDER BY month, revenue DESC
            LIMIT 200
        """,
        rationale="Aggregate synthetic order revenue at month and region grain.",
    ),
    _Template(
        plan_id="top_products",
        title="Top products by revenue",
        examples=("Show the top 5 products by revenue", "Gelire göre en iyi 5 ürünü göster"),
        keyword_groups=(
            ("top", "best", "en iyi", "en cok"),
            ("product", "urun"),
            ("revenue", "gelir", "ciro"),
        ),
        sql="""
            SELECT
                p.product_name,
                p.category,
                ROUND(SUM(o.gross_revenue), 2) AS revenue
            FROM orders AS o
            JOIN products AS p ON p.product_id = o.product_id
            GROUP BY p.product_id, p.product_name, p.category
            ORDER BY revenue DESC
            LIMIT 5
        """,
        rationale="Join the synthetic product catalog and rank products by aggregated revenue.",
    ),
    _Template(
        plan_id="refund_rate_by_region",
        title="Refund rate by region",
        examples=("Compare refund rate by region", "Bölgelere göre iade oranını karşılaştır"),
        keyword_groups=(("refund", "iade"), ("region", "bolge")),
        sql="""
            SELECT
                region,
                COUNT(*) AS orders,
                ROUND(100.0 * SUM(refunded) / COUNT(*), 2) AS refund_rate_pct
            FROM orders
            GROUP BY region
            ORDER BY refund_rate_pct DESC
            LIMIT 200
        """,
        rationale="Calculate a bounded aggregate over synthetic refund flags.",
    ),
    _Template(
        plan_id="last_30_days",
        title="Last 30 days performance",
        examples=(
            "Show orders and revenue for the last 30 days",
            "Son 30 günün sipariş ve gelirini göster",
        ),
        keyword_groups=(("last 30", "son 30"), ("order", "siparis"), ("revenue", "gelir", "ciro")),
        sql="""
            SELECT
                order_date,
                COUNT(*) AS orders,
                ROUND(SUM(gross_revenue), 2) AS revenue
            FROM orders
            WHERE order_date >= date(:as_of_date, '-29 days')
            GROUP BY order_date
            ORDER BY order_date
            LIMIT 200
        """,
        rationale=" ".join(
            (
                "Use the fixed synthetic dataset date as an explicit, reproducible",
                "reporting boundary.",
            )
        ),
    ),
    _Template(
        plan_id="average_order_value_by_channel",
        title="Average order value by channel",
        examples=(
            "Compare average order value by channel",
            "Kanala göre ortalama sipariş değerini karşılaştır",
        ),
        keyword_groups=(
            ("average", "ortalama"),
            ("order value", "siparis degeri"),
            ("channel", "kanal"),
        ),
        sql="""
            SELECT
                channel,
                COUNT(*) AS orders,
                ROUND(AVG(gross_revenue), 2) AS average_order_value
            FROM orders
            GROUP BY channel
            ORDER BY average_order_value DESC
            LIMIT 200
        """,
        rationale="Compare synthetic order value at the sales-channel grain.",
    ),
)


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    ascii_like = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_like = ascii_like.replace("ı", "i")
    return re.sub(r"\s+", " ", ascii_like).strip()


def supported_questions() -> tuple[str, ...]:
    return tuple(template.examples[0] for template in _TEMPLATES)


def compile_question(question: str) -> QueryPlan:
    if not isinstance(question, str):
        raise TypeError("question must be a string")
    cleaned = question.strip()
    if not 3 <= len(cleaned) <= 500:
        raise ValueError("question must contain between 3 and 500 characters")
    if any(ord(char) < 32 and char not in "\t\n\r" for char in cleaned):
        raise ValueError("question contains unsupported control characters")

    normalized = _normalize(cleaned)
    scored: list[tuple[int, _Template]] = []
    for template in _TEMPLATES:
        matched_groups = sum(
            any(_normalize(keyword) in normalized for keyword in group)
            for group in template.keyword_groups
        )
        scored.append((matched_groups, template))

    best_score, best_template = max(scored, key=lambda item: item[0])
    if best_score < len(best_template.keyword_groups):
        examples = "; ".join(supported_questions())
        raise UnsupportedQuestionError(
            "This public demo intentionally supports a bounded question catalog. "
            f"Try one of: {examples}"
        )

    parameters = (
        {"as_of_date": DEMO_AS_OF_DATE.isoformat()}
        if best_template.plan_id == "last_30_days"
        else {}
    )
    return QueryPlan(
        plan_id=best_template.plan_id,
        title=best_template.title,
        question=cleaned,
        sql="\n".join(line.rstrip() for line in best_template.sql.strip().splitlines()),
        parameters=parameters,
        rationale=best_template.rationale,
    )
