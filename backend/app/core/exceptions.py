class MediSimplifyException(Exception):
    """Base exception for all MediSimplify AI errors."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ValidationError(MediSimplifyException):
    """Exception raised when input validation fails."""
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


class ResourceNotFoundError(MediSimplifyException):
    """Exception raised when a resource is not found."""
    def __init__(self, message: str):
        super().__init__(message, status_code=404)


class ExtractionError(MediSimplifyException):
    """Exception raised when text or structured data extraction fails."""
    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class ProviderError(MediSimplifyException):
    """Exception raised when an external service provider (LLM, STT, TTS) fails."""
    def __init__(self, message: str):
        super().__init__(message, status_code=502)
