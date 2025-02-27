import functools
import grpc
import logging
import re

from flask import request
from flask_restful import Resource

from grpc_api.messages import user_pb2, user_pb2_grpc
from errors import HttpError

logger = logging.getLogger(__name__)

stub = user_pb2_grpc.UserServiceStub(grpc.insecure_channel('localhost:50051'))


def handle_grpc_error(e):
    """
    Handles gRPC errors and returns appropriate HTTP responses.

    Args:
        e: The gRPC RpcError exception.

    Returns:
        tuple: A dictionary containing the error message and the corresponding
               HTTP status code.
    """
    if isinstance(e, grpc.Call):
        grpc_code = e.code()
        details = e.details()
    else:
        grpc_code = grpc.StatusCode.UNKNOWN
        details = "Unknown gRPC error"

    logger.error(f"gRPC error occurred: {grpc_code} - {details}")

    if grpc_code == grpc.StatusCode.NOT_FOUND:
        return {"error": HttpError.NOT_FOUND.message}, HttpError.NOT_FOUND.code
    elif grpc_code == grpc.StatusCode.INVALID_ARGUMENT:
        return {"error": HttpError.BAD_REQUEST.format_message(details)}, HttpError.BAD_REQUEST.code
    elif grpc_code == grpc.StatusCode.UNAUTHENTICATED:
        return {"error": HttpError.UNAUTHORIZED.message}, HttpError.UNAUTHORIZED.code
    elif grpc_code == grpc.StatusCode.ALREADY_EXISTS:
        return {"error": HttpError.ALREADY_EXISTS.message}, HttpError.ALREADY_EXISTS.code
    else:
        return {
            "error": "Unexpected gRPC error"}, HttpError.INTERNAL_SERVER_ERROR.code


def handle_exceptions(func):
    """
    Decorator to handle exceptions for API methods.

    Args:
        func (function): The API function being wrapped.

    Returns:
        function: A wrapped function with standardized error handling.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            return {"error": str(e)}, HttpError.BAD_REQUEST.code
        except grpc.RpcError as rpc_error:
            return handle_grpc_error(rpc_error)
        except Exception as e:
            logger.critical(f"Unexpected internal server error: {e}", exc_info=True)
            return {
                "error": HttpError.INTERNAL_SERVER_ERROR.format_message(str(e))}, HttpError.INTERNAL_SERVER_ERROR.code

    return wrapper


def sanitize_nickname(nickname):
    """
    Sanitizes and validates a given nickname.

    Ensures the nickname:
    - Is lowercase.
    - Contains only letters (a-z), hyphens (-), and underscores (_).
    - Has no spaces.
    - Is at least 3 characters long.

    Args:
        nickname (str): The user-provided nickname.

    Returns:
        str: A sanitized and valid nickname.

    Raises:
        ValueError: If the nickname contains invalid characters or is too short.
    """
    if not isinstance(nickname, str) or not nickname.strip():
        raise ValueError("Nickname cannot be empty.")

    nickname = nickname.lower().replace(" ", "")

    if len(nickname) < 3:
        raise ValueError("Nickname must be at least 3 characters long.")

    if not re.match(r"^[a-z-_]+$", nickname):
        raise ValueError("Nickname can only contain letters (a-z), hyphens (-), and underscores (_)")

    return nickname


def sanitize_password(password):
    """
    Sanitizes a given password.

    Ensures the password:
    - Has no spaces.
    - Is at least 5 characters long.

    Args:
        password (str): The user-provided password.

    Returns:
        str: A sanitized and valid password.

    Raises:
        ValueError: If the password contains invalid characters or is too short.
    """
    if not isinstance(password, str) or not password.strip():
        raise ValueError("Password cannot be empty.")

    password = password.replace(" ", "")

    if len(password) < 3:
        raise ValueError("Password must be at least 5 characters long.")

    return password


class User(Resource):
    """
    Manages operations related to a specific user.

    This resource provides endpoints for:
    - Retrieving a user by nickname.
    - Deleting a user.

    Responsibilities:
    - Interacts with the gRPC service to fetch or remove user data.
    - Validates incoming request data before processing.
    - Handles potential errors and exceptions.

    Methods:
        - get(nickname): Retrieves a specific user by nickname.
        - delete(nickname): Deletes a user by nickname.
    """

    @handle_exceptions
    def get(self, nickname):
        """
        Retrieves a specific user by their unique nickname.

        Args:
            nickname (str): The unique nickname of the user.

        Returns:
            tuple:
                - dict: A JSON response containing the user's data if found.
                - int: The corresponding HTTP status code.

        Response Example:
        ```json
        {
            "id": "124",
            "name": "John Smith",
            "nickname": "john_smith",
            "about": "Blog about John Smith"
            "profile_img_url": "https://aws.amazon.com/s3/example.jpg"
            "followers": 48,
            "following": 14,
            "member_since": "2024-02-26T10:00:00Z"
        }
        ```
        """
        sanitize_nickname(nickname)
        user_response = stub.GetUser(user_pb2.GetUserRequest(nickname=nickname))

        return self._build_user_response(user_response.user), HttpError.OK.code

    @handle_exceptions
    def delete(self, nickname):
        """
        Deletes a specific user by nickname.

        Args:
             nickname (str): The unique nickname of the user.

        Returns:
            user_pb2.DeleteUserResponse: The deleted user's response (FAILED or SUCCESS)
        """
        sanitize_nickname(nickname)

        user_response = stub.DeleteUser(user_pb2.DeleteUserRequest(nickname=nickname))

        if user_response.status == "FAILED":
            return {"error": user_response.message}, HttpError.NOT_FOUND.code

        return {"message": user_response.message}, HttpError.OK.code

    def _build_user_response(self, user):
        """
        Converts a gRPC response to a dictionary representing a user.

        Args:
            user (user_pb2 Response): A gRPC response.

        Returns:
            dict: The user's data converted to a dictionary.
        """
        return {
            "id": user.id,
            "name": user.name,
            "nickname": user.nickname,
            "about": user.about,
            "profile_img_url": user.profile_img_url,
            "followers": user.followers,
            "following": user.following,
            "member_since": user.member_since,
        }


class UserList(Resource):
    """
    Manages operations related to a collection of users.

    This resource provides endpoints for:
    - Retrieving all users.
    - Creating a new user.

    Responsibilities:
    - Fetches user data from the gRPC service.
    - Sends user creation requests to the gRPC service.
    - Handles potential errors and exceptions.

    Methods:
        - get(): Retrieves a list of all users.
        - post(): Creates a new user.
    """

    def __init__(self):
        """Initialize with an instance of UserResource to reuse its methods."""
        self.user_resource = User()

    @handle_exceptions
    def get(self):
        """
        Retrieves a collection of all users.

        Returns:
            tuple: A JSON response containing the collection of users and an HTTP status code.

        Response Example:
        ```json
        {
            "users": [
                {
                    "id": "124",
                    "name": "John Smith",
                    "nickname": "john_smith",
                    "about": "Blog about John Smith"
                    "profile_img_url": "https://aws.amazon.com/s3/example.jpg"
                    "followers": 48,
                    "following": 14,
                    "member_since": "2024-02-26T10:00:00Z"
                }
                {
                    "id": "124",
                    "name": "Mark",
                    "nickname": "Mark",
                    "about": "Blog about Mark"
                    "profile_img_url": "https://aws.amazon.com/s3/example.jpg"
                    "followers": 12,
                    "following": 76,
                    "member_since": "2024-02-26T10:00:00Z"
                }
            ]
        }
        ```
        """
        user_response = stub.GetCollectionUsers(user_pb2.GetCollectionUsersRequest())

        users_data = [self.user_resource._build_user_response(user) for user in user_response.users]

        return {"users": users_data}, HttpError.OK.code


class UserUpdate(Resource):
    """
    Manages operations related to a specific user.

    This resource provides endpoints for:
    - Updating user details.

    Responsibilities:
    - Interacts with the gRPC service modify user data.
    - Validates incoming request data before processing.
    - Handles potential errors and exceptions.

    Methods:
        - put(id): Updates user information.
    """

    @handle_exceptions
    def put(self, user_id):
        """
        Updates a specific user by user_id.

        Args:
            user_id (int): The unique ID of the user.

        Returns:
            tuple: A JSON response with the updated user's data.

        Request Body Example:
        ```json
        {
            "name": "Updated John Smith",
            "nickname": "updated_john_smith",
            "about": "Updated blog about John Smith",
            "profile_img_url": "https://aws.amazon.com/s3/updated-example.jpg",
            "current_password": "old_password123",
            "new_password": "new_secure_password"
        }
        ```

        Response Example:
        ```json
        {
            {
                "id": "124",
                "name": "Updated John Smith",
                "nickname": "updated_john_smith",
                "about": "Updated blog about John Smith"
                "profile_img_url": "https://aws.amazon.com/s3/updated-example.jpg"
                "followers": 12,
                "following": 76,
                "member_since": "2024-02-26T10:00:00Z"
            }
        }
        ```
        """
        new_data = request.get_json()

        user_response = stub.UpdateUser(self._update_user_instance(new_data, user_id))

        return self._build_update_user_response(user_response.user), HttpError.OK.code

    def _update_user_instance(self, new_data, user_id):
        """
        Creates an update user instance with sanitized nickname.

        Args:
            new_data (dict): Dictionary containing the user's new data.
            user_id (int): The unique ID of the user.

        Returns:
            user_pb2.UpdateUserRequest: The gRPC request object for updating the user.
        """
        validated_nickname = sanitize_nickname(new_data["nickname"]) if "nickname" in new_data else None
        validated_password = sanitize_password(new_data["new_password"]) if "new_password" in new_data else None

        return user_pb2.UpdateUserRequest(
            id=user_id,
            name=new_data.get("name", None),
            about=new_data.get("about", None),
            nickname=validated_nickname,
            current_password=new_data.get("current_password", None),
            new_password=validated_password,
            profile_img_url=new_data.get("profile_img_url", None),
        )

    def _build_update_user_response(self, user):
        """
        Converts a gRPC response to a dictionary representing a user.

        Args:
            user (user_pb2 Response): A gRPC response.

        Returns:
            dict: The user's data converted to a dictionary.
        """
        return {
            "id": user.id,
            "name": user.name,
            "nickname": user.nickname,
            "about": user.about,
            "profile_img_url": user.profile_img_url,
            "followers": user.followers,
            "following": user.following,
            "member_since": user.member_since,
        }
