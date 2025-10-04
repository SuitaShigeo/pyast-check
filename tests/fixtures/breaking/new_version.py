"""New API version with breaking changes."""

MAX_RETRIES = "three"  # type changed: int -> str
TIMEOUT = 30

# process function removed entirely

def greet(name: str, formal: bool) -> str:  # required parameter added
    if formal:
        return f"Good day, {name}"
    return f"Hello, {name}"

def validate(value: int) -> int:  # return type changed
    return max(value, 0)

class Service:
    def __init__(self, name: str) -> None:
        self.name = name

    def start(self) -> bool:  # return type changed (but not breaking at class level)
        return True

    # stop method removed
