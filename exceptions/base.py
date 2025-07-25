"""Base exception classes for Scrible Wise"""

from typing import Any


class ScribbleWiseError(Exception):
    """Base exception for all Scrible Wise errors"""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        recovery_suggestion: str | None = None,
        can_retry: bool = False,
        max_retries: int = 0,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.recovery_suggestion = recovery_suggestion
        self.can_retry = can_retry
        self.max_retries = max_retries

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for serialization"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "recovery_suggestion": self.recovery_suggestion,
        }
