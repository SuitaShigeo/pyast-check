"""Validation utilities."""


def validate(value: int) -> bool:
    """Check if value is positive."""
    if value <= 0:
        return False
    return True
