"""Old API version."""

MAX_RETRIES = 3
TIMEOUT = 30

def process(data: list) -> None:
    for item in data:
        print(item)

def greet(name: str) -> str:
    return f"Hello, {name}"

def validate(value: int) -> bool:
    return value > 0

class Service:
    def __init__(self, name: str) -> None:
        self.name = name

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
