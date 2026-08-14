from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any
from urllib.parse import urlsplit

from ..catalog import UnsupportedQuestionError
from ..service import QueryTimeoutError, TalkToYourDataDemo

MAX_REQUEST_BYTES = 8_192
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class DemoServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int]) -> None:
        super().__init__(address, DemoHandler)
        self.service = TalkToYourDataDemo()


class DemoHandler(BaseHTTPRequestHandler):
    server: DemoServer
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _security_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        content_security_policy = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
        )
        self.send_header("Content-Security-Policy", content_security_policy)
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")

    def _send_bytes(self, status: HTTPStatus, content_type: str, payload: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self._security_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send_bytes(status, "application/json; charset=utf-8", encoded)

    def _valid_host(self) -> bool:
        raw_host = self.headers.get("Host", "")
        hostname = raw_host.rsplit(":", 1)[0].strip("[]").casefold()
        return hostname in LOOPBACK_HOSTS

    def _valid_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        parsed = urlsplit(origin)
        return parsed.scheme == "http" and (parsed.hostname or "").casefold() in LOOPBACK_HOSTS

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        if not self._valid_host():
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_host"})
            return
        if self.path == "/":
            html = files("talk_to_your_data_demo.web").joinpath("index.html").read_bytes()
            self._send_bytes(HTTPStatus.OK, "text/html; charset=utf-8", html)
            return
        if self.path == "/api/health":
            self._send_json(HTTPStatus.OK, {"status": "ok", "mode": "offline_synthetic"})
            return
        if self.path == "/api/questions":
            self._send_json(
                HTTPStatus.OK,
                {
                    "questions": list(self.server.service.questions()),
                    "stats": self.server.service.stats(),
                },
            )
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
        if self.path != "/api/ask":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if not self._valid_host() or not self._valid_origin():
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "request_origin_rejected"})
            return
        content_type = self.headers.get("Content-Type", "")
        if not content_type.casefold().startswith("application/json"):
            self._send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "json_required"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        if not 1 <= content_length <= MAX_REQUEST_BYTES:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "request_too_large"})
            return
        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            if not isinstance(payload, dict) or not isinstance(payload.get("question"), str):
                raise ValueError("question must be a string")
            result = self.server.service.ask(payload["question"])
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValueError,
            UnsupportedQuestionError,
        ) as error:
            self._send_json(
                HTTPStatus.BAD_REQUEST, {"error": "invalid_question", "message": str(error)}
            )
            return
        except QueryTimeoutError as error:
            self._send_json(
                HTTPStatus.REQUEST_TIMEOUT, {"error": "query_timeout", "message": str(error)}
            )
            return
        self._send_json(HTTPStatus.OK, result.to_dict())


def build_server(host: str = "127.0.0.1", port: int = 8765) -> DemoServer:
    if host.casefold() not in LOOPBACK_HOSTS:
        raise ValueError("the public demo server is intentionally loopback-only")
    if not 0 <= port <= 65_535:
        raise ValueError("port must be between 0 and 65535")
    return DemoServer((host, port))


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = build_server(host=host, port=port)
    actual_port = server.server_address[1]
    print(f"Talk to Your Data demo: http://{host}:{actual_port}")
    print("Synthetic data only. Press Ctrl+C to stop.")
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
