import grpc

from flask import request
from flask_restful import Resource

from grpc_api.messages import user_pb2, user_pb2_grpc
from errors import HttpError, GrpcError

stub = user_pb2_grpc.UserServiceStub(grpc.insecure_channel('localhost:50051'))


class UserResource(Resource):
    """
    Handles a specific user operations
    Provides retrieving, updating and deleting a user
    """

    def get(self, nickname):
        """
        Retrieves a specific user by nickname.

        Args:
            nickname (str): The unique nickname of the user.

        Returns:
            dict: The user's data if found.

        Raises:
            ValueError: If the given nickname is invalid.
            NotFoundError: If the user is not found.
            grpc.RpcError: If an RPC-related error occurs.
        """
        try:
            self._validate_nickname(nickname)
            user_response = stub.GetUser(user_pb2.GetUserRequest(nickname=nickname.strip()))

            return self._build_user_response(user_response.user), HttpError.OK.code

        except ValueError as e:
            return {"error": HttpError.BAD_REQUEST.format_message(str(e))}, HttpError.BAD_REQUEST.code

        except grpc.RpcError as e:
            raise self._handle_grpc_error(e)

        except Exception as e:
            return ({"error": HttpError.INTERNAL_SERVER_ERROR.format_message(str(e))},
                    HttpError.INTERNAL_SERVER_ERROR.code)

    def put(self, nickname, new_data):
        """
        Updates a specific user by nickname.

        Args:
            new_data (dict): The user's new data.
            nickname (str): The unique nickname of the user.

        Returns:
            dict: The updated user's data

        Raises:
            ValueError: If the given nickname is invalid.
            NotFoundError: If the user is not found.
            grpc.RpcError: If an RPC-related error occurs.
        """
        try:
            self._validate_nickname(nickname)

            update_request = user_pb2.UpdateUserRequest(
                name=new_data.get("name", ""),
                about=new_data.get("about", ""),
                nickname=new_data.get("nickname", "").strip(),
                profile_img_url=new_data.get("profile_img_url", ""),
            )

            user_response = stub.UpdateUser(update_request)

            return self._build_user_response(user_response.user), HttpError.OK.code

        except ValueError as e:
            return {"error": HttpError.BAD_REQUEST.format_message(str(e))}, HttpError.BAD_REQUEST.code

        except grpc.RpcError as e:
            return self._handle_grpc_error(e)

        except Exception as e:
            return ({"error": HttpError.INTERNAL_SERVER_ERROR.format_message(str(e))},
                    HttpError.INTERNAL_SERVER_ERROR.code)

    def delete(self, nickname):
        """
        Deletes a specific user by nickname.

        Args:
             nickname (str): The unique nickname of the user.

        Returns:
            user_pb2.DeleteUserResponse: The deleted user's response (FAILED or SUCCESS)

        Raises:
            ValueError: If the given nickname is invalid.
            NotFoundError: If the user is not found.
            grpc.RpcError: If an RPC-related error occurs.
        """
        try:
            self._validate_nickname(nickname)

            user_response = stub.DeleteUser(user_pb2.DeleteUserRequest(nickname=nickname.strip()))

            if user_response.status == "FAILED":
                return {"error": user_response.message}, HttpError.NOT_FOUND.code

            return {"message": user_response.message}, HttpError.OK.code

        except ValueError as e:
            return {"error": HttpError.BAD_REQUEST.format_message(str(e))}, HttpError.BAD_REQUEST.code

        except grpc.RpcError as e:
            return self._handle_grpc_error(e)

        except Exception as e:
            return ({"error": HttpError.INTERNAL_SERVER_ERROR.format_message(str(e))},
                    HttpError.INTERNAL_SERVER_ERROR.code)

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

    def _handle_grpc_error(self, error: grpc.RpcError):
        """
        Handles gRPC errors and maps them to HTTP responses.

        Args:
            error (grpc.RpcError): The gRPC exception.

        Returns:
            dict: JSON error response.
            int: Corresponding HTTP status code.
        """
        grpc_to_http_map = {
            grpc.StatusCode.NOT_FOUND: ({"error": "User not found"}, HttpError.NOT_FOUND.code),
            grpc.StatusCode.INVALID_ARGUMENT: ({"error": "Invalid request parameters"}, HttpError.BAD_REQUEST.code),
            grpc.StatusCode.PERMISSION_DENIED: ({"error": "Permission denied"}, HttpError.FORBIDDEN.code),
            grpc.StatusCode.INTERNAL: ({"error": "Internal server error"}, HttpError.INTERNAL_SERVER_ERROR.code),
        }

        return grpc_to_http_map.get(error.code(),
                                    ({"error": error}, HttpError.INTERNAL_SERVER_ERROR.code))

    def _validate_nickname(self, nickname):
        """
        Validates the user nickname.

        Args:
            nickname (str): The nickname to validate.

        Raises:
            ValueError: If the nickname is empty or invalid.
        """
        if not nickname or not nickname.strip():
            raise ValueError("The nickname is empty or invalid.")

        if len(nickname) < 3:
            raise ValueError("Nickname must be at least 3 characters long.")


class UserListResource(Resource):
    """
    Handles a collection of user operations
    Provides retrieving all users and creating a new user
    """

    def __init__(self):
        """Initialize with an instance of UserResource to reuse its methods."""
        self.user_resource = UserResource()

    def get(self):
        """
        Retrieves a collection of all users.

        Returns:
            tuple: A JSON response with the collection of users and HTTP status code.

        Raises:
            grpc.RpcError: If an RPC-related error occurs.
        """
        try:
            user_response = stub.GetCollectionUsers(user_pb2.GetCollectionUsersRequest())

            users_data = [self.user_resource._build_user_response(user) for user in user_response.users]

            return {"users": users_data}, HttpError.OK.code

        except grpc.RpcError as e:
            return self.user_resource._handle_grpc_error(e)

    def post(self):
        """
        Creates a new user.

        Returns:
            tuple: A JSON response with the newly created user and HTTP status code.

        Raises:
            ValueError: If the given data is invalid.
            grpc.RpcError: If an RPC-related error occurs.
        """
        try:
            new_user = request.get_json()

            if not new_user:
                return {"error": "Request body cannot be empty"}, HttpError.BAD_REQUEST.code

            self._check_required_fields(new_user)

            create_request = user_pb2.CreateUserRequest(
                name=new_user.get("name", ""),
                about=new_user.get("about", ""),
                nickname=new_user.get("nickname", ""),
                profile_img_url=new_user.get("profile_img_url", ""),
            )

            user_response = stub.CreateUser(create_request)
            return self.user_resource._build_user_response(user_response.user), HttpError.OK.code

        except ValueError as e:
            return {"error": str(e)}, HttpError.BAD_REQUEST.code

        except grpc.RpcError as e:
            return self.user_resource._handle_grpc_error(e)

        except Exception as e:
            return {"error": HttpError.INTERNAL_SERVER_ERROR.format_message(
                str(e))}, HttpError.INTERNAL_SERVER_ERROR.code

    def _check_required_fields(self, new_user):
        """
        Checks if the given user has required fields.

        Args:
            new_user (dict): The user's data to check.

        Raises:
            ValueError: If any required fields are missing.
        """
        required_fields = ["name", "nickname"]
        missing_fields = [field for field in required_fields if field not in new_user]

        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        return True
