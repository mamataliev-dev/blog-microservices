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
        return {"error": HttpError.BAD_REQUEST.message}, HttpError.BAD_REQUEST.code
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


class UserResource(Resource):
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


class UserListResource(Resource):
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
        self.user_resource = UserResource()

    @handle_exceptions
    def get(self):
        """
        Retrieves a collection of all users.

        Returns:
            tuple: A JSON response containing the collection of users and an HTTP status code.
        """
        user_response = stub.GetCollectionUsers(user_pb2.GetCollectionUsersRequest())

        users_data = [self.user_resource._build_user_response(user) for user in user_response.users]

        return {"users": users_data}, HttpError.OK.code

    @handle_exceptions
    def post(self):
        """
        Handles the creation of a new user.

        Returns:
            tuple: A JSON response containing the newly created user's data and an HTTP status code.
        """
        new_user = request.get_json()

        if not new_user:
            return {"error": "Request body cannot be empty"}, HttpError.BAD_REQUEST.code

        sanitize_nickname(new_user["nickname"])
        self._check_required_fields(new_user)

        user_response = stub.CreateUser(self._create_post_user_instance(new_user))

        return self.user_resource._build_user_response(user_response.user), HttpError.CREATED.code

    def _check_required_fields(self, new_user):
        """
        Validates the presence of required fields in the given user data.

        Args:
            new_user (dict): The user's data to check.

        Returns:
            bool: True if all required fields are present and non-empty.

        Raises:
            ValueError: If any required fields are missing or empty.
        """
        required_fields = ["name", "nickname"]
        missing_fields = [field for field in required_fields if not new_user.get(field)]

        if missing_fields:
            logger.error(f"Missing or empty required fields: {', '.join(missing_fields)}")
            raise ValueError(f"Missing or empty required fields: {', '.join(missing_fields)}")

        return True

    def _create_post_user_instance(self, new_user):
        """
        Creates a new user instance.

        Args:
            new_user: Dictionary containing the new user's data.

        Returns:
            dict: The converted user instance.
        """
        return user_pb2.CreateUserRequest(
            name=new_user["name"],
            about=new_user["about"],
            nickname=new_user["nickname"],
            profile_img_url=new_user["profile_img_url"],
        )


class UserResourceById(Resource):
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

    def __init__(self):
        """Initialize with an instance of UserResource to reuse its methods."""
        self.user_resource = UserResource()

    @handle_exceptions
    def put(self, user_id):
        """
        Updates a specific user by user_id.

        Args:
            user_id (int): The unique ID of the user.

        Returns:
            tuple: A JSON response with the updated user's data.
        """
        new_data = request.get_json()
        if not new_data:
            return {"error": "Request body cannot be empty"}, HttpError.BAD_REQUEST.code

        user_response = stub.UpdateUser(self._update_user_instance(new_data, user_id))

        return self.user_resource._build_user_response(user_response.user), HttpError.OK.code

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

        return user_pb2.UpdateUserRequest(
            id=user_id,
            name=new_data.get("name", None),
            about=new_data.get("about", None),
            nickname=validated_nickname,
            profile_img_url=new_data.get("profile_img_url", None),
        )
