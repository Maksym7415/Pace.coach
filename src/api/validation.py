"""Shared request validation helpers."""

MIN_PASSWORD_LEN = 10


def validate_password(password) -> str | None:
    """
    Return an error message if the password is invalid, otherwise None.

    Policy: minimum length only (aligned with registration and reset flows).
    """
    if password is None or not str(password).strip():
        return "Password is required"
    if len(str(password)) < MIN_PASSWORD_LEN:
        return f"Password must be at least {MIN_PASSWORD_LEN} characters long"
    return None
