"""Conversion-related exceptions"""

from typing import Any

from .base import ScribbleWiseError


class ConversionError(ScribbleWiseError):
    """Exception raised during media conversion"""

    def __init__(
        self,
        message: str,
        input_path: str | None = None,
        output_path: str | None = None,
        error_code: str | None = None,
        recovery_suggestion: str | None = None,
        can_retry: bool = False,
        max_retries: int = 0,
    ):
        super().__init__(
            message, error_code, recovery_suggestion, can_retry, max_retries
        )
        self.input_path = input_path
        self.output_path = output_path

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for serialization"""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "input_path": self.input_path,
                "output_path": self.output_path,
            }
        )
        return base_dict
