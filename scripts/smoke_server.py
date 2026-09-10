#!/usr/bin/env python3
"""Smoke test for step 2: POST a string to the HTTP API and see it at the cursor.

Starts a real ThreadingHTTPServer on an ephemeral port, calls the real endpoint with
urllib, and finally compares the bytes the capture window received.

    uv run scripts/smoke_server.py
"""

import json
import sys
import threading
import urllib.error
import urllib.request

from _harness import capture_window, wait_for_text
from remote_input.server import create_server

# Non-ASCII on purpose: the text has to survive HTTP, D-Bus and the terminal untouched.
TEXT = "HTTP round-trip: Grüße, мир 123"


def request(port: int, path: str, body: bytes | None = None) -> tuple[int, bytes]:
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with urllib.request.urlopen(url, body, timeout=5) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def main() -> int:
    server = create_server("127.0.0.1", 0)
    port = server.server_port
    threading.Thread(target=server.serve_forever, daemon=True).start()

    failures: list[str] = []
    try:
        status, body = request(port, "/")
        if status != 200 or b"/api/commit" not in body:
            failures.append(f"GET / -> {status} {body[:80]!r}")

        status, body = request(port, "/api/commit", b"not json")
        if status != 400:
            failures.append(f"POST /api/commit (bad body) -> {status} {body!r}")

        status, body = request(port, "/api/nope", b"{}")
        if status != 404:
            failures.append(f"POST /api/nope -> {status} {body!r}")

        with capture_window() as capture:
            payload = json.dumps({"text": TEXT}).encode()
            status, body = request(port, "/api/commit", payload)
            if status != 200 or json.loads(body) != {"committed": True}:
                failures.append(f"POST /api/commit -> {status} {body!r}")
            actual = wait_for_text(capture, TEXT)

        if actual != TEXT:
            failures.append(f"cursor received {actual!r}")
    finally:
        server.shutdown()
        server.server_close()

    if failures:
        print("FAIL:\n  " + "\n  ".join(failures), file=sys.stderr)
        return 1
    print(f"PASS: POST /api/commit {TEXT!r} landed at the cursor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
