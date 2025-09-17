from fastapi import HTTPException


class _ApiError(HTTPException):
    def __init__(self, detail: str, status_code: int):
        super().__init__(detail=detail, status_code=status_code)


class _InternalError(Exception):
    def __init__(self, detail: str):
        super().__init__(detail)


class ApiBadRequest(_ApiError):
    def __init__(self, detail: str):
        status_code = 400
        detail = "Bad Request: " + detail
        super().__init__(detail=detail, status_code=status_code)


class ApiInternalError(_ApiError):
    def __init__(self, detail: str):
        status_code = 500
        detail = "Internal Error: " + detail
        super().__init__(detail=detail, status_code=status_code)


class MissingInformationError(_InternalError):
    """Custom exception for missing information.

    Args:
        message (str): The error message describing the missing information.
    """

    def __init__(self, message: str):
        super().__init__(message)


class HallucinationInputError(Exception):
    def __init__(
        self,
        field_name: str,
        field_value: str,
        message: str = "Hallucination tool input detected",
    ):
        self.field_name: str = field_name
        self.field_value: str = field_value
        self.message: str = f"{message} in {field_name}: {field_value}"
        super().__init__(self.message)


class FailedExternalAPI(_InternalError):
    """The error for the failed external API call.

    Args:
        detail (str): inherited from the API error message.
    """

    def __init__(self, detail: str):
        super().__init__(detail)


class APIKeyServiceError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code: int = status_code
        self.message: str = message
        super().__init__(f"API key service error: {status_code} - {message}")


class BaseAppException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message: str = message
        self.status_code: int = status_code
        super().__init__(message)


class ServicesAuthenticationError(BaseAppException):
    """Raised when authentication to a service fails (e.g. invalid API key)."""

    def __init__(self, message: str = "Invalid API key or unauthorized access"):
        super().__init__(status_code=401, message=message)


class GenericServiceError(BaseAppException):
    """Generic error for external services with HTTP status code.

    Use this when the specific service name is not known or irrelevant.

    Args:
        status_code (int): HTTP status code from the external service.
        message (str): Error message describing the failure.
    """

    def __init__(self, status_code: int, message: str):
        super().__init__(status_code=status_code, message=message)


class ResourceNotFound(_InternalError):
    """Custom exception for resource not found.

    Args:
        message (str): The error message indicating the resource does not exist.
    """

    def __init__(self, message: str):
        super().__init__(message)
