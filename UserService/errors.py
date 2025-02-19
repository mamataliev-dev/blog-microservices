import grpc
from enum import Enum


class GrpcError(Enum):
    """
    An enumeration of gRPC error codes and their corresponding error messages.

    This class provides a centralized way to handle and format gRPC errors.
    Each enum member represents a specific error condition, including:
    - The gRPC status code.
    - A descriptive error message (which can be dynamically formatted).

    Usage:
    - Use the enum members to represent specific error conditions.
    - Use the `format_message` method to dynamically insert values into error messages.
    """
    OK = (grpc.StatusCode.OK, "OK")
    USER_NOT_FOUND = (grpc.StatusCode.NOT_FOUND, "User not found")
    INVALID_ARGUMENT = (grpc.StatusCode.INVALID_ARGUMENT, "Invalid request parameters")
    INTERNAL_SERVER_ERROR = (grpc.StatusCode.INTERNAL, "An internal server error occurred")
    ALREADY_EXISTS = (grpc.StatusCode.ALREADY_EXISTS, "User already exists")
    DATABASE_ERROR = (grpc.StatusCode.INTERNAL, "Database error: {}")
    INTERNAL = (grpc.StatusCode.INTERNAL, "Internal server error: {}")

    def __init__(self, code, message):
        self.code = code
        self.message = message

    def format_message(self, *args):
        """Dynamically formats the error message with provided arguments."""
        return self.message.format(*args)


class HttpError(Enum):
    """
    An enumeration of HTTP status codes and their corresponding error messages.

    This class provides a centralized way to handle HTTP errors in a web application.
    Each enum member represents a specific HTTP error condition, including:
    - The HTTP status code (e.g., 404 for "Not Found").
    - A descriptive error message (which can be dynamically formatted).

    Usage:
    - Use the enum members to represent specific HTTP error conditions.
    - Access the `code` and `message` attributes to construct error responses.
    """
    OK = (200, "OK")
    NOT_FOUND = (404, "User not found")
    BAD_REQUEST = (400, "Invalid request parameters")
    INTERNAL_SERVER_ERROR = (500, "An internal server error occurred: {}")
    FORBIDDEN = (403, "You do not have permission to perform this action")
    CONFLICT = (409, "User already exists")
    DATABASE_ERROR = (500, "Database error: {}")
    UNEXPECTED_ERROR = (500, "Unexpected server error: {}")
    UNAUTHORIZED = (401, "Unauthorized")
    SERVICE_UNAVAILABLE = (500, "Service unavailable")
    ALREADY_EXISTS = (409, "Nickname already taken")
    CREATED = (201, "User created successfully")

    def __init__(self, code, message):
        self.code = code
        self.message = message

    def format_message(self, *args):
        """Dynamically formats the error message with provided arguments."""
        return self.message.format(*args)
