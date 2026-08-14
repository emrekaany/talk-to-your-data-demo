import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from talk_to_your_data_demo.web.server import build_server


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = build_server(port=0)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def test_health_and_index(self) -> None:
        with urlopen(self._url("/api/health"), timeout=2) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response)["mode"], "offline_synthetic")
        with urlopen(self._url("/"), timeout=2) as response:
            html = response.read().decode("utf-8")
            self.assertIn("Ask a business question", html)
            self.assertEqual(response.headers["X-Frame-Options"], "DENY")

    def test_ask_endpoint(self) -> None:
        request = Request(
            self._url("/api/ask"),
            method="POST",
            data=json.dumps({"question": "Compare refund rate by region"}).encode(),
            headers={"Content-Type": "application/json", "Origin": f"http://127.0.0.1:{self.port}"},
        )
        with urlopen(request, timeout=2) as response:
            payload = json.load(response)
        self.assertEqual(payload["plan"]["plan_id"], "refund_rate_by_region")
        self.assertEqual(payload["synthetic_source_rows"], 720)

    def test_cross_origin_request_is_rejected(self) -> None:
        request = Request(
            self._url("/api/ask"),
            method="POST",
            data=b'{"question":"Compare refund rate by region"}',
            headers={"Content-Type": "application/json", "Origin": "https://attacker.invalid"},
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=2)
        try:
            self.assertEqual(raised.exception.code, 403)
        finally:
            raised.exception.close()

    def test_public_bind_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "loopback-only"):
            build_server(host="0.0.0.0", port=0)


if __name__ == "__main__":
    unittest.main()
