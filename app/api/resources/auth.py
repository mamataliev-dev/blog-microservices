import logging
import grpc

from flask import request
from flask_restful import Resource
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity

from grpc_api.messages import user_pb2
from app.api.resources.user import handle_exceptions, sanitize_nickname, sanitize_password, stub
from errors import HttpError

logger = logging.getLogger(__name__)


class Register(Resource):
    @handle_exceptions
    def post(self):
        """
        Handles the creation of a new user.

        Returns:
            tuple: A JSON response containing the newly created user's data and an HTTP status code.

        Request Body Example:
        ```json
        {
            "name": "John Smith",
            "nickname": "john_smith",
            "about": "Blog about John Smith",
            "profile_img_url": "https://aws.amazon.com/s3/example.jpg",
            "new_password": "new_secure_password"
        }
        ```

        Response Example:
        ```json
        {
            {
                "id": "124",
                "name": "John Smith",
                "nickname": "john_smith",
                "about": "Blog about John Smith"
                "profile_img_url": "https://aws.amazon.com/s3/example.jpg"
                "followers": 12,
                "following": 76,
                "member_since": "2024-02-26T10:00:00Z"
            }
        }
        ```
        """
        new_user = request.get_json()

        if not new_user:
            return {"error": "Request body cannot be empty"}, HttpError.BAD_REQUEST.code

        sanitize_nickname(new_user["nickname"])
        sanitize_password(new_user["password"])
        self._check_required_fields(new_user)

        user_response = stub.CreateUser(self._create_new_user_instance(new_user))

        return self._build_new_user_response(user_response.user), HttpError.CREATED.code

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
        required_fields = ["name", "nickname", "password"]
        missing_fields = [field for field in required_fields if not new_user.get(field)]

        if missing_fields:
            logger.error(f"Missing or empty required fields: {', '.join(missing_fields)}")
            raise ValueError(f"Missing or empty required fields: {', '.join(missing_fields)}")

        return True

    def _create_new_user_instance(self, new_user):
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
            password=new_user["password"],
            profile_img_url=new_user["profile_img_url"],
        )

    def _build_new_user_response(self, user):
        return {
            "id": user.id,
            "name": user.name,
            "nickname": user.nickname,
            "about": user.about,
            "profile_img_url": user.profile_img_url,
            "followers": user.followers,
            "following": user.following,
            "member_since": user.member_since,
            "access_token": create_access_token(identity=user.nickname),
        }


class Login(Resource):
    """
    API Resource for user authentication.

    This endpoint handles user login by validating credentials and generating
    a JWT access token upon successful authentication.
    """

    @handle_exceptions
    def post(self):
        """
        Handles the POST request for user login.

        Request:
        - JSON Body:
          ```json
          {
            "nickname": "example_user",
            "password": "secure_password"
          }
          ```

        Returns:
        - JSON Response:
          ```json
          {
            "access_token": "JWT_TOKEN_HERE"
          }
          ```
        """
        data = request.get_json()

        nickname = sanitize_nickname(data["nickname"])
        password = sanitize_password(data["password"])

        stub.GetUser(user_pb2.LoginUserRequest(nickname=nickname, password=password))

        return {"access_token": create_access_token(identity=nickname)}, 200


class Logout(Resource):
    @jwt_required()
    def post(self):
        pass
