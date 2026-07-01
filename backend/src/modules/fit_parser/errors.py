"""Structured errors raised by the FIT parser."""


class FitParserError(Exception):
    """Base class for FIT parser errors."""


class InvalidFitFileError(FitParserError):
    """Raised when input is not a valid FIT file."""


class CorruptedFitFileError(FitParserError):
    """Raised when a FIT file is truncated or otherwise corrupted."""


class UnsupportedFormatError(FitParserError):
    """Raised when a FIT file uses an unsupported layout or format."""
