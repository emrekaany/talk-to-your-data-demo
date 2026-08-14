from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta

DEMO_AS_OF_DATE = date(2026, 7, 31)
SYNTHETIC_SEED = 20260814

_PRODUCTS = (
    (1, "Atlas Bottle", "Accessories", 18.0),
    (2, "Beacon Lamp", "Home", 34.0),
    (3, "Cedar Desk", "Home", 240.0),
    (4, "Drift Headphones", "Electronics", 85.0),
    (5, "Ember Keyboard", "Electronics", 72.0),
    (6, "Field Backpack", "Accessories", 58.0),
    (7, "Grove Chair", "Home", 130.0),
    (8, "Harbor Charger", "Electronics", 29.0),
    (9, "Iris Notebook", "Stationery", 8.0),
    (10, "Juniper Pen Set", "Stationery", 14.0),
    (11, "Kite Monitor", "Electronics", 195.0),
    (12, "Lumen Organizer", "Accessories", 26.0),
)


def build_demo_connection() -> sqlite3.Connection:
    """Return an isolated in-memory database containing deterministic fake data."""

    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(
        """
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            unit_price REAL NOT NULL CHECK (unit_price > 0)
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            order_date TEXT NOT NULL,
            region TEXT NOT NULL,
            channel TEXT NOT NULL,
            product_id INTEGER NOT NULL REFERENCES products(product_id),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            gross_revenue REAL NOT NULL CHECK (gross_revenue >= 0),
            refunded INTEGER NOT NULL CHECK (refunded IN (0, 1))
        );

        CREATE INDEX idx_orders_date ON orders(order_date);
        CREATE INDEX idx_orders_product ON orders(product_id);
        """
    )
    connection.executemany(
        "INSERT INTO products(product_id, product_name, category, unit_price) VALUES (?, ?, ?, ?)",
        _PRODUCTS,
    )

    rng = random.Random(SYNTHETIC_SEED)
    regions = ("North", "South", "West")
    channels = ("Web", "Mobile", "Partner")
    rows: list[tuple[object, ...]] = []
    first_day = DEMO_AS_OF_DATE - timedelta(days=179)
    order_id = 1
    for day_offset in range(180):
        order_day = first_day + timedelta(days=day_offset)
        for order_in_day in range(4):
            product = _PRODUCTS[(day_offset * 3 + order_in_day * 5) % len(_PRODUCTS)]
            quantity = 1 + rng.randrange(4)
            seasonality = 1.0 + (day_offset / 1800.0)
            gross_revenue = round(product[3] * quantity * seasonality, 2)
            refunded = int(rng.random() < (0.035 + (order_in_day * 0.008)))
            rows.append(
                (
                    order_id,
                    order_day.isoformat(),
                    regions[(day_offset + order_in_day) % len(regions)],
                    channels[(day_offset * 2 + order_in_day) % len(channels)],
                    product[0],
                    quantity,
                    gross_revenue,
                    refunded,
                )
            )
            order_id += 1

    connection.executemany(
        """
        INSERT INTO orders(
            order_id, order_date, region, channel, product_id,
            quantity, gross_revenue, refunded
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    connection.commit()
    connection.execute("PRAGMA query_only = ON")
    return connection


def demo_stats(connection: sqlite3.Connection) -> dict[str, object]:
    order_count, first_date, last_date = connection.execute(
        "SELECT COUNT(*), MIN(order_date), MAX(order_date) FROM orders"
    ).fetchone()
    product_count = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    return {
        "orders": int(order_count),
        "products": int(product_count),
        "first_date": str(first_date),
        "last_date": str(last_date),
        "synthetic": True,
        "seed": SYNTHETIC_SEED,
    }
