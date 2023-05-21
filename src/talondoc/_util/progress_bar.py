import awesome_progress_bar


class ProgressBar:
    def __init__(self, total: int, show: bool = True) -> None:
        self.line_width = 0
        self.show = show
        if self.show:
            self.bar = awesome_progress_bar.ProgressBar(
                prefix="",
                total=total,
                bar_length=30,
                use_thread=False,
                use_spinner=False,
            )

    def step(self, msg: str = "") -> None:
        self.line_width = max(self.line_width, len(msg))
        pad = self.line_width - len(msg)
        if self.show:
            self.bar.iter(msg + pad * " ")
