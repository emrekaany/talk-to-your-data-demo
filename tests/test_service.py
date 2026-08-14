import unittest

from talk_to_your_data_demo.service import TalkToYourDataDemo


class ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = TalkToYourDataDemo()

    def test_synthetic_dataset_is_deterministic(self) -> None:
        self.assertEqual(
            self.service.stats(),
            {
                "orders": 720,
                "products": 12,
                "first_date": "2026-02-02",
                "last_date": "2026-07-31",
                "synthetic": True,
                "seed": 20260814,
            },
        )

    def test_every_supported_question_executes(self) -> None:
        for question in self.service.questions():
            with self.subTest(question=question):
                result = self.service.ask(question)
                self.assertTrue(result.rows)
                self.assertLessEqual(len(result.rows), 200)
                self.assertEqual(result.synthetic_source_rows, 720)
                self.assertFalse(result.truncated)
                self.assertIn("LIMIT", result.plan.sql)

    def test_results_are_reproducible(self) -> None:
        first = self.service.ask("Show the top 5 products by revenue").to_dict()
        second = self.service.ask("Show the top 5 products by revenue").to_dict()
        first.pop("elapsed_ms")
        second.pop("elapsed_ms")
        self.assertEqual(first, second)

    def test_timeout_configuration_is_bounded(self) -> None:
        with self.assertRaises(ValueError):
            TalkToYourDataDemo(timeout_ms=0)
        with self.assertRaises(ValueError):
            TalkToYourDataDemo(timeout_ms=10_000)


if __name__ == "__main__":
    unittest.main()
