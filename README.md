# remote-input

Type or dictate on your phone, and the text lands at the cursor of the window that is
focused on your desktop: phone browser → HTTP → fcitx5 commit → active window.

```
┌────────┐  POST /api/commit   ┌──────────────┐   D-Bus Commit   ┌──────────────────┐
│ phone  │ ──────────────────► │ remote-input │ ───────────────► │ fcitx5 addon     │
│ browser│ ◄────────────────── │  (Python)    │                  │ commitString() → │
└────────┘   {"committed":…}   └──────────────┘                  │ focused window   │
                                                                 └──────────────────┘
```

## Why a compiled addon is required

fcitx5 has no D-Bus API to commit text: `Controller1` only carries activate/deactivate/
switch-input-method style calls, and `commitString()` is only reachable from inside the
fcitx5 process. The `CommitString` you find on the bus is a **signal** of the frontend
interface (fcitx5 → application), which a third-party process cannot call.

So the twenty-line C++ addon in `addon/` exists to expose that single seam:

```
org.fcitx.Fcitx5  /remoteinput  org.fcitx.Fcitx.RemoteInput1.Commit(s) -> b
```

Why not fake keystrokes with wtype/ydotool: a commit does not travel through the input
method engine, so the engine never turns the text into preedit/candidates on the way in.

## Requirements

- fcitx5 5.1.x (developed against 5.1.22) including its headers — the Arch `fcitx5`
  package ships them
- `g++` and `pkg-config` (Arch: `pacman -S base-devel pkgconf`)
- [uv](https://docs.astral.sh/uv/) (it manages the Python 3.14 interpreter itself)
- a graphical session with Wayland + input-method-v2 (tested on Hyprland)
- `foot` — only needed by the smoke scripts, which use it as a capture window

## Deployment

### 1. Install the addon

```bash
bash addon/install.sh
```

Everything goes into your home directory; no root is needed:

| Path | What |
|---|---|
| `~/.local/lib/fcitx5/remoteinput.so` | the compiled addon |
| `~/.local/share/fcitx5/addon/remoteinput.conf` | addon description (confs use the regular XDG dirs) |
| `~/.config/environment.d/50-remote-input.conf` | `FCITX_ADDON_DIRS=~/.local/lib/fcitx5:<libdir>/fcitx5` |

**Note:** do not shorten that last line: fcitx5 looks for addon `.so` files only in
`FCITX_ADDON_DIRS` plus the built-in addon dir (the `<libdir>/fcitx5` entry, which the
script derives from `pkg-config --variable=libdir Fcitx5Core`), and **once
`FCITX_ADDON_DIRS` is set, the built-in directory is no longer appended
automatically** — so it has to be listed explicitly, otherwise every system addon
(wayland, keyboard, your input method engines, …) stops loading too.

### 2. Restart fcitx5

```bash
busctl --user call org.fcitx.Fcitx5 /controller org.fcitx.Fcitx.Controller1 Exit
```

DBus activation or your systemd unit brings it back within a few seconds. Check that the
addon got loaded:

```bash
busctl --user call org.fcitx.Fcitx5 /controller org.fcitx.Fcitx.Controller1 GetAddons \
  | tr ' ' '\n' | grep remoteinput
```

### 3. Verify

```bash
uv run scripts/smoke_fcitx.py
```

### 4. Run the server

```bash
uv run remote-input --port 8765     # listens on 0.0.0.0 by default
```

Open `http://<your-desktop-lan-ip>:8765/` on your phone, and click the target window on
your desktop first — the text goes to the *focused* input context, not to a window you
pick in the page.

### 5. Optional: start at login

`~/.config/systemd/user/remote-input.service`:

```ini
[Unit]
Description=remote input (phone -> fcitx5)
After=graphical-session.target
PartOf=graphical-session.target

[Service]
ExecStart=%h/remote-input/.venv/bin/remote-input --port 8765
Restart=on-failure

[Install]
WantedBy=graphical-session.target
```

Adjust `ExecStart` to the path you cloned the project into, then:

```bash
systemctl --user daemon-reload
systemctl --user enable --now remote-input.service
```

## Smoke scripts

| Script | What it proves |
|---|---|
| `uv run scripts/smoke_fcitx.py` | fcitx5 commits a string verbatim to the cursor (step 1) |
| `uv run scripts/smoke_server.py` | `POST /api/commit` reaches the cursor, plus the 400/404 branches (step 2) |

Both need a graphical session, but they discover `XDG_RUNTIME_DIR`/`WAYLAND_DISPLAY`
themselves, so they also run from a plain tty. Each one opens a `foot` window as the
"cursor" (`stty raw -echo; cat > file`) and only commits once that window really holds
focus — never typing blind into whatever window you happen to be using. Focus detection
uses `hyprctl`; on other compositors there is no focus check, so keep the desktop idle
while the smoke runs.

## HTTP API

```
POST /api/commit   {"text": "..."}
                   → 200 {"committed": true|false}    false = no focused input context
                   → 400   body is not {"text": "..."}
                   → 503   fcitx5 or the addon is unavailable

GET  /             → the minimal web UI (src/remote_input/static/index.html)
```

## The phone page

Three things: a text box, a `Send` button, and an `Auto-send N s` setting.

- All controls sit in **one row at the top**, the text box takes the rest: a phone
  soft keyboard slides up from the bottom, so bottom-anchored controls get covered.
- `0` (default): manual only, tap `Send`.
- `N>0`: commit automatically N seconds after typing stops, then clear the box.
  A countdown is shown right below the controls row.
- Text is **not** committed while a mobile IME is composing; the timer only starts at
  `compositionend`, i.e. once the final text has settled.
- The number is kept in the phone browser's localStorage, so it survives reloads.
- If a commit fails (e.g. no focused input context yet) the text stays in the box and is
  **not** retried automatically — click the target window on the desktop first, then tap
  `Send`.

## Uninstall

```bash
rm ~/.local/lib/fcitx5/remoteinput.so \
   ~/.local/share/fcitx5/addon/remoteinput.conf \
   ~/.config/environment.d/50-remote-input.conf
# then restart fcitx5 (see step 2)
```

## Troubleshooting

| Symptom | Cause |
|---|---|
| `GetAddons` does not list `remoteinput` | `FCITX_ADDON_DIRS` did not take effect: restart fcitx5 after changing it; when editing from another terminal also run `systemctl --user set-environment` (`install.sh` does this for you) |
| 503 `ServiceUnknown` | fcitx5 is not running |
| `{"committed": false}` | no focused input context: click the target window on the desktop first |
| Text lands in the wrong window | a commit goes to the *focused* window — focus the target window before sending |

## Known limitations

- The server has no authentication: anyone on the same LAN / tailnet can type onto your
  screen. Put a token in front of it if you expose it beyond a trusted network.
- One commit at a time; there are no "press Enter / Backspace / clear" actions.
