"""Custom exceptions for Deep Biblio Tools."""


class DeepBiblioError(Exception):
    """Base exception for all Deep Biblio Tools errors."""

    pass


class BibliographyError(DeepBiblioError):
    """Base exception for bibliography-related errors."""

    pass


class ParsingError(BibliographyError):
    """Error parsing bibliography file or entry."""

    def __init__(self, message: str, structured_error=None):
        super().__init__(message)
        self.structured_error = structured_error


class ValidationError(BibliographyError):
    """Validation error in bibliography entry."""

    def __init__(self, message: str, structured_error=None):
        super().__init__(message)
        self.structured_error = structured_error


class FormattingError(BibliographyError):
    """Error formatting bibliography entry or citation key."""

    pass


class ResolutionError(BibliographyError):
    """Error resolving bibliography data from external sources."""

    pass


class DuplicateKeyError(BibliographyError):
    """Duplicate citation key detected."""

    pass


class MissingFieldError(ValidationError):
    """Required field missing in bibliography entry."""

    pass


class InvalidFieldError(ValidationError):
    """Invalid field value in bibliography entry."""

    pass


class APIError(DeepBiblioError):
    """Error communicating with external API."""

    pass


class RateLimitError(APIError):
    """API rate limit exceeded."""

    pass


class ConversionError(DeepBiblioError):
    """Error during document conversion."""

    pass


class MarkdownError(ConversionError):
    """Error processing Markdown content."""

    pass


class LaTeXError(ConversionError):
    """Error processing LaTeX content."""

    pass
