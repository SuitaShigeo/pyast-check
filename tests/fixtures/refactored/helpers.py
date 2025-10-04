"""Helper classes."""


class Helper:
    """A helper class."""

    def __init__(self, name: str) -> None:
        self.name = name

    def run(self) -> str:
        return f"Running {self.name}"
