"""HTTP layer: hand the text of a POST over to fcitx5, and serve the small web UI.

Nothing but plumbing between HTTP and remote_input.fcitx -- no input method knowledge
lives here.
"""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import urlsplit

from .fcitx import Fcitx5Unavailable, commit

_INDEX = files("remote_input") / "static" / "index.html"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        if urlsplit(self.path).path == "/":
            self._send(200, _INDEX.read_bytes(), "text/html; charset=utf-8")
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/commit":
            self._json(404, {"error": "not found"})
            return

        try:
            text = json.loads(self._body())["text"]
            if not isinstance(text, str):
                raise TypeError
        except (json.JSONDecodeError, KeyError, TypeError, UnicodeDecodeError):
            self._json(400, {"error": 'expected JSON body {"text": "..."}'})
            return

        try:
            committed = commit(text)
        except Fcitx5Unavailable as error:
            self._json(503, {"error": str(error)})
            return
        self._json(200, {"committed": committed})

    def _body(self) -> bytes:
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self._send(status, body, "application/json; charset=utf-8")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(host: str, port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="type on your phone, land the text at the cursor on your desktop"
    )
    parser.add_argument("--host", default="0.0.0.0", help="bind address (default: all interfaces)")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = create_server(args.host, args.port)
    print(f"listening on http://{args.host}:{server.server_port}/", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
