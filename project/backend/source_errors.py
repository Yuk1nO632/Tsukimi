"""Playback-provider errors mapped to HTTP responses by FastAPI."""


class SourceError(Exception):
    def __init__(self, message: str, status_code: int = 502, reason: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.reason = reason
