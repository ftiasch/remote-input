"""Shared scaffolding for the smoke scripts: session environment plus a "cursor".

The capture window is a foot window in the user's graphical session running
`stty raw -echo; cat > file`, so every byte that reaches the cursor is written to that
file verbatim and can be compared byte for byte.
"""

import contextlib
import glob
import os
import pathlib
import subprocess
import tempfile
import time

APP_ID = "remote-input-smoke"
FOCUS_TIMEOUT = 10.0
SETTLE_TIMEOUT = 2.0


def session_env() -> dict[str, str]:
    """Fill in the variables a graphical session needs, so this also runs from a tty."""
    env = dict(os.environ)
    runtime = env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    if "WAYLAND_DISPLAY" not in env:
        sockets = [
            path
            for path in sorted(glob.glob(f"{runtime}/wayland-*"))
            if not path.endswith(".lock")
        ]
        if not sockets:
            raise RuntimeError(f"no wayland socket under {runtime}; run me in the session")
        env["WAYLAND_DISPLAY"] = os.path.basename(sockets[0])
    signature = list(pathlib.Path(f"{runtime}/hypr").glob("*"))
    if signature and "HYPRLAND_INSTANCE_SIGNATURE" not in env:
        env["HYPRLAND_INSTANCE_SIGNATURE"] = signature[0].name
    return env


def focused_app_id(env: dict[str, str]) -> str | None:
    """app-id of the focused window; None when it cannot be determined."""
    try:
        result = subprocess.run(
            ["hyprctl", "activewindow"], env=env, capture_output=True, text=True
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.strip().startswith("class:"):
            return line.split(":", 1)[1].strip()
    return None


@contextlib.contextmanager
def capture_window(env: dict[str, str] | None = None):
    """Open a capture window, wait for its focus, yield the capture file path."""
    env = env or session_env()
    with tempfile.TemporaryDirectory() as tmp:
        capture = pathlib.Path(tmp) / "captured"
        window = subprocess.Popen(
            ["foot", "-a", APP_ID, "-e", "sh", "-c", f"stty raw -echo; cat > {capture}"],
            env=env,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            deadline = time.monotonic() + FOCUS_TIMEOUT
            while time.monotonic() < deadline:
                # Never commit while the capture window is not focused: the text would
                # go into whatever window the user is working in.
                if focused_app_id(env) in (APP_ID, None):
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError(f"{APP_ID} never got focus; refusing to type blind")
            yield capture
        finally:
            os.killpg(window.pid, 15)


def capture_text(capture: pathlib.Path) -> str:
    return capture.read_text(encoding="utf-8") if capture.exists() else ""


def wait_for_text(capture: pathlib.Path, expected: str) -> str:
    """Wait until the capture file contains expected, then return what it holds."""
    deadline = time.monotonic() + SETTLE_TIMEOUT
    while time.monotonic() < deadline:
        actual = capture_text(capture)
        if actual == expected:
            return actual
        time.sleep(0.05)
    return capture_text(capture)
