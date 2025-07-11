from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Label

def format_bytes(bytes_value, color=True, decimal=2):
    if isinstance(bytes_value, str):
        return bytes_value

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0

    while bytes_value >= 1024 and unit_index < len(units) - 1:
        bytes_value /= 1024
        unit_index += 1

    # Format with specified rounding precision
    formatted_value = f"{bytes_value:.{decimal}f}"

    # Remove unnecessary ".00" if rounding results in a whole number
    if formatted_value.endswith(f".{'0' * decimal}"):
        formatted_value = formatted_value[: -decimal - 1]

    if bytes_value == 0:
        return "0"
    elif color:
        return f"{formatted_value}[highlight]{units[unit_index]}[/highlight]"
    else:
        return f"{formatted_value}{units[unit_index]}"

class TopBar(Container):
    host = reactive("", init=False, always_update=True)
    replay_file_size = reactive("", always_update=True)

    def __init__(
        self, connection_status="", app_version="", host="", help="press [b highlight]q[/b highlight] to return"
    ):
        super().__init__()

        self.app_title = Text.from_markup(f" :dolphin: [b light_blue]Dolphie[/b light_blue] [light_blue]v{app_version}")

        self.topbar_title = Label(self.app_title, id="topbar_title")
        self.topbar_host = Label("", id="topbar_host")
        self.topbar_help = Label(Text.from_markup(help), id="topbar_help")

        self.connection_status = connection_status
        self.host = host
        self.replay_file_size = None

    def _update_topbar_host(self):
        recording_text = (
            f"| [b recording]RECORDING[/b recording]: {format_bytes(self.replay_file_size)}"
            if self.replay_file_size
            else ""
        )
        self.topbar_host.update(
            Text.from_markup(
                f"\\[[white]{self.connection_status}[/white]] {self.host} {recording_text}"
                if self.connection_status
                else ""
            )
        )

    def watch_replay_file_size(self):
        self._update_topbar_host()

    def watch_host(self):
        self._update_topbar_host()

    def compose(self) -> ComposeResult:
        yield self.topbar_title
        yield self.topbar_host
        yield self.topbar_help