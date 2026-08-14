import unittest

from talk_to_your_data_demo.catalog import (
    UnsupportedQuestionError,
    compile_question,
    supported_questions,
)


class CatalogTests(unittest.TestCase):
    def test_every_documented_question_compiles(self) -> None:
        plans = [compile_question(question) for question in supported_questions()]
        self.assertEqual(len(plans), 5)
        self.assertEqual(len({plan.plan_id for plan in plans}), 5)

    def test_turkish_question_compiles(self) -> None:
        plan = compile_question("Bölgelere göre aylık geliri göster")
        self.assertEqual(plan.plan_id, "monthly_revenue_by_region")

    def test_last_30_days_uses_explicit_boundary(self) -> None:
        plan = compile_question("Show orders and revenue for the last 30 days")
        self.assertEqual(plan.parameters, {"as_of_date": "2026-07-31"})

    def test_unsupported_question_fails_with_examples(self) -> None:
        with self.assertRaisesRegex(UnsupportedQuestionError, "bounded question catalog"):
            compile_question("Predict next year's customer lifetime value")

    def test_question_size_and_type_are_bounded(self) -> None:
        with self.assertRaises(TypeError):
            compile_question(7)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            compile_question("ab")
        with self.assertRaises(ValueError):
            compile_question("x" * 501)


if __name__ == "__main__":
    unittest.main()
