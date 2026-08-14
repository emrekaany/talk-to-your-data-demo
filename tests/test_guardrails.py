import sqlite3
import unittest

from talk_to_your_data_demo.guardrails import (
    QueryPolicyError,
    install_read_only_authorizer,
    validate_read_only_sql,
)
from talk_to_your_data_demo.synthetic import build_demo_connection


class GuardrailTests(unittest.TestCase):
    def test_valid_query_passes(self) -> None:
        validate_read_only_sql("SELECT order_id FROM orders LIMIT 10")

    def test_write_and_pragma_statements_fail(self) -> None:
        for sql in (
            "DELETE FROM orders LIMIT 1",
            (
                "WITH x AS (SELECT order_id FROM orders LIMIT 1) "
                "UPDATE orders SET refunded = 1 LIMIT 1"
            ),
            "PRAGMA table_info(orders) LIMIT 1",
        ):
            with self.subTest(sql=sql), self.assertRaises(QueryPolicyError):
                validate_read_only_sql(sql)

    def test_comments_multistatement_and_select_star_fail(self) -> None:
        for sql in (
            "SELECT order_id FROM orders -- comment\nLIMIT 1",
            "SELECT order_id FROM orders LIMIT 1; SELECT 1",
            "SELECT * FROM orders LIMIT 1",
        ):
            with self.subTest(sql=sql), self.assertRaises(QueryPolicyError):
                validate_read_only_sql(sql)

    def test_unknown_table_and_unbounded_query_fail(self) -> None:
        with self.assertRaisesRegex(QueryPolicyError, "outside the allowlist"):
            validate_read_only_sql("SELECT secret_value FROM secrets LIMIT 1")
        with self.assertRaisesRegex(QueryPolicyError, "LIMIT"):
            validate_read_only_sql("SELECT order_id FROM orders")
        with self.assertRaisesRegex(QueryPolicyError, "LIMIT"):
            validate_read_only_sql("SELECT order_id FROM orders LIMIT 201")

    def test_sqlite_authorizer_blocks_writes_even_after_validation_layer(self) -> None:
        connection = build_demo_connection()
        install_read_only_authorizer(connection)
        with self.assertRaises(sqlite3.DatabaseError):
            connection.execute("DELETE FROM orders")
        connection.close()


if __name__ == "__main__":
    unittest.main()
