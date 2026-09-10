#!/usr/bin/env python3
"""Smoke test for step 1: can fcitx5 commit a string verbatim to the cursor?

    uv run scripts/smoke_fcitx.py
"""

import sys

from _harness import capture_window, wait_for_text
from remote_input.fcitx import commit

# Non-ASCII on purpose: the text has to survive D-Bus and the terminal untouched.
TEXT = "Grüße, мир — café 123"


def main() -> int:
    with capture_window() as capture:
        if not commit(TEXT):
            print("FAIL: commit() reported no input context", file=sys.stderr)
            return 1
        actual = wait_for_text(capture, TEXT)

    if actual != TEXT:
        print(f"FAIL: cursor received {actual!r}", file=sys.stderr)
        return 1
    print(f"PASS: {TEXT!r} landed at the cursor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
