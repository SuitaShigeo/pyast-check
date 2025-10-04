"""Sample original module for testing."""

__all__ = ["greet", "farewell", "Helper", "MAX_RETRIES", "validate"]

MAX_RETRIES = 3

TIMEOUT = 30


def greet(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"


def farewell(name: str) -> str:
    """Say goodbye."""
    return f"Goodbye, {name}!"


def validate(value: int) -> bool:
    """Check if value is positive."""
    if value <= 0:
        return False
    return True


def _internal_helper(x: int) -> int:
    return x * 2


class Helper:
    """A helper class."""

    def __init__(self, name: str) -> None:
        self.name = name

    def run(self) -> str:
        return f"Running {self.name}"
