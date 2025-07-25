"""Scrible Wise Custom Exceptions Module

This module provides a hierarchy of custom exceptions for the Scrible Wise
audio transcription tool, enabling precise error handling and recovery.
"""

from .base import ScribbleWiseError
from .conversion import ConversionError
from .transcription import TranscriptionError
from .validation import ValidationError

__all__ = [
    "ScribbleWiseError",
    "ConversionError",
    "TranscriptionError",
    "ValidationError",
]
