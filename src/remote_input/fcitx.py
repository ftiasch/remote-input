"""Commit text into fcitx5, landing it at the cursor.

fcitx5 itself has no D-Bus API to commit text: Controller1 only carries activate /
deactivate / switch-input-method style calls, and commitString() is only reachable from
inside the fcitx5 process. This module therefore talks to the remoteinput addon in
addon/, which exposes that single seam:

    org.fcitx.Fcitx5  /remoteinput  org.fcitx.Fcitx.RemoteInput1.Commit(s) -> b

Compared to faking keystrokes (wtype/ydotool), a commit never travels through the input
method engine, so the engine cannot turn the text into preedit or candidate selections
on the way in.
"""

from jeepney import DBusAddress, new_method_call
from jeepney.io.blocking import open_dbus_connection
from jeepney.wrappers import DBusErrorResponse

_COMMIT_ADDRESS = DBusAddress(
    "/remoteinput",
    bus_name="org.fcitx.Fcitx5",
    interface="org.fcitx.Fcitx.RemoteInput1",
)


class Fcitx5Unavailable(RuntimeError):
    """fcitx5 or the remoteinput addon is not usable."""


def commit(text: str) -> bool:
    """Commit text into the current input context; False if there is none."""
    connection = open_dbus_connection(bus="SESSION")
    try:
        reply = connection.send_and_get_reply(
            new_method_call(_COMMIT_ADDRESS, "Commit", "s", (text,))
        )
    except DBusErrorResponse as error:
        # Mostly: fcitx5 is not running (ServiceUnknown), or the addon is not
        # installed (UnknownMethod / UnknownInterface).
        raise Fcitx5Unavailable(f"commit failed: {error}") from error
    finally:
        connection.close()
    return reply.body[0]
