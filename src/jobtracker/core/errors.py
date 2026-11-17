from __future__ import annotations


class JobTrackerError(Exception):
    """An expected failure, reported to callers as an error code and message."""

    def __init__(self, code: str, message: str, **details: object) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self) -> dict:
        error: dict = {"code": self.code, "message": self.message}
        if self.details:
            error["details"] = self.details
        return error
