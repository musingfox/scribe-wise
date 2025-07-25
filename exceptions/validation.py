"""Validation-related exceptions"""

from typing import Any

from .base import ScribbleWiseError


class ValidationError(ScribbleWiseError):
    """Exception raised during validation"""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        validation_issues: list[str] | None = None,
        error_code: str | None = None,
        recovery_suggestion: str | None = None,
        can_retry: bool = False,
        max_retries: int = 0,
    ):
        super().__init__(
            message, error_code, recovery_suggestion, can_retry, max_retries
        )
        self.file_path = file_path
        self.validation_issues = validation_issues or []

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for serialization"""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "file_path": self.file_path,
                "validation_issues": self.validation_issues,
            }
        )
        return base_dict
