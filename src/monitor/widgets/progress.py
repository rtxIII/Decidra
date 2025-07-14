from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.reactive import reactive
from textual.widgets import Label, ProgressBar


class ProgressBar(Vertical):
    SCOPED_CSS = False
    DEFAULT_CSS = """
    ProgressBar {
        width: 100%;
        height: auto;
        margin: 2 4;
        dock: top;                    
        padding: 1 2;
        background: $primary;        
        display: block;
        text-align: center;
        display: none;
        align: center top;       
        ProgressBar {
            margin: 1 0;
        } 
    }

    LogLines:focus ProgressBar.-has-content {
        display: block;
    }
    """

    message = reactive("")
    complete = reactive(0.0)

    def watch_message(self, message: str) -> None:
        self.query_one(".message", Label).update(message)
        self.set_class(bool(message), "-has-content")

    def compose(self) -> ComposeResult:
        with Center():
            yield Label(classes="message")
        with Center():
            yield ProgressBar(total=1.0, show_eta=True, show_percentage=True).data_bind(
                progress=ProgressBar.complete
            )