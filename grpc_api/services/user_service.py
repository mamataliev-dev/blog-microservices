from datetime import datetime

from sqlalchemy import Executable

from app.models import User
from app.extensions import db
from errors import GrpcError
from grpc_api.messages import user_pb2, user_pb2_grpc
from app import create_app

from werkzeug.security import generate_password_hash
from sqlalchemy.exc import SQLAlchemyError
from flask_jwt_extended import create_access_token, get_jwt_identity

app = create_app()


class UserService(user_pb2_grpc.UserServiceServicer):
    """
    A gRPC service for managing user operations.

    This class implements the gRPC servicer for handling user-related operations.
    It provides methods to:
        - Retrieve a specific user by nickname.
        - Retrieve a collection of all users.
        - Create a new user.
        - Update an existing user.
        - Delete a user by nickname.

    This service communicates with a database to perform CRUD operations on user data.

    Methods:
        GetUser(request, context):
            Retrieves a user by their unique nickname.

        GetCollectionUsers(request, context):
            Retrieves a list of all users in the database.

        CreateUser(request, context):
            Creates a new user with the provided details.

        UpdateUser(request, context):
            Updates an existing user's information based on the given data.

        DeleteUser(request, context):
            Deletes a user from the database using their nickname.

    Args:
        user_pb2_grpc.UserServiceServicer:
            The base class for defining gRPC service methods.
    """

    def GetUser(self, request, context):
        """
        Retrieves a specific user by nickname.

        Args:
            request: The gRPC request containing the user's nickname.
            context: The gRPC context for handling metadata and status codes.

        Returns:
            user_pb2.GetUserResponse:
                - A response containing the user’s details if found.
                - An empty response if the user does not exist.

        Raises:
            grpc.RpcError.NOT_FOUND:
                - If the user with the given nickname is not found in the database.
            grpc.RpcError.INTERNAL:
                - If an unexpected error occurs while retrieving the user.
        """
        user = self._find_user_by_nickname(request.nickname, context)

        if not user:
            context.set_code(GrpcError.NOT_FOUND.code)
            context.set_details("User not found.")
            return user_pb2.GetUserResponse()

        return self._build_user_response(user, user_pb2.GetUserResponse)

    def GetCollectionUsers(self, request, context):
        """
        Retrieves a collection of users.

        Args:
            request: The gRPC request (empty for this method).
            context: The gRPC context for handling metadata and status codes.

        Returns:
            user_pb2.GetCollectionUsersResponse:
                - A response containing the list of users if successful.
                - An empty response if no users are found or an error occurs.

        Raises:
            grpc.RpcError.INTERNAL:
                - If an error occurs while fetching users from the database.
        """
        users = self._fetch_collection_users()
        user_responses = [self._build_collection_user_response(user, user_pb2.User) for user in users]
        return user_pb2.GetCollectionUsersResponse(users=user_responses)

    def UpdateUser(self, request, context):
        """
        Updates existing user by ID.

        Args:
            request: The gRPC request containing the user's new data.
            context: The gRPC context for handling metadata and status codes.

        Returns:
            user_pb2.UpdateUserResponse:
                - A response containing the updated user data if successful.
                - An empty response if the user update fails.

        Raises:
            grpc.RpcError.NOT_FOUND:
                - If the user with the given nickname does not exist.
            grpc.RpcError.INTERNAL:
                - If an error occurs while updating the user in the database.
        """
        try:
            with app.app_context():
                user = self._fetch_user_by_id(request.id)

                if not user:
                    return user_pb2.UpdateUserResponse()

                updated_user = self._update_user_by_id(user, request, context)

                if not updated_user:
                    return user_pb2.UpdateUserResponse()

                return self._build_user_response(updated_user, user_pb2.UpdateUserResponse)

        except Exception as e:
            context.set_code(GrpcError.INTERNAL)
            context.set_details(GrpcError.INTERNAL.format_message(str(e)))
            return user_pb2.UpdateUserResponse()

    def CreateUser(self, request, context):
        """
        Creates a new user in the database.

        Args:
            request: The gRPC request containing the user data.
            context: The gRPC context for handling metadata and status codes.

        Returns:
            user_pb2.CreateUserResponse:
                - A response containing the newly created user's data if successful.
                - An empty response if user creation fails.

        Raises:
            grpc.RpcError.INVALID_ARGUMENT:
                - If the request data is invalid or missing required fields.
            grpc.RpcError.ALREADY_EXISTS:
                - If the provided nickname already exists in the database.
            grpc.RpcError.INTERNAL:
                - If a database error or an unexpected server error occurs.
        """
        try:
            new_user = self._create_user_in_db(request, context)
            if not new_user:
                return user_pb2.CreateUserResponse()

            return self._build_user_response(new_user, user_pb2.CreateUserResponse)

        except Exception as e:
            context.set_code(GrpcError.INTERNAL)
            context.set_details(GrpcError.INTERNAL.format_message(str(e)))
            return user_pb2.CreateUserResponse()

    def DeleteUser(self, request, context):
        """
        Deletes a user by their nickname.

        Args:
            request: The gRPC request containing the user's nickname.
            context: The gRPC context for handling metadata and status codes.

        Returns:
            user_pb2.DeleteUserResponse:
                - A response indicating the deletion status:
                    - "SUCCESS" if the user was successfully deleted.
                    - "FAILED" if the user was not found.

        Raises:
            grpc.RpcError.NOT_FOUND:
                - If no user with the given nickname exists.
            grpc.RpcError.INTERNAL:
                - If an unexpected database error occurs during deletion.
        """
        user = self._find_user_by_nickname(request.nickname, context)

        if not user:
            context.set_code(GrpcError.NOT_FOUND.code)
            context.set_details("User not found.")
            return user_pb2.DeleteUserResponse(status="FAILED", message="User not found")

        return self._delete_user_by_nickname(user, context)

    def LoginUser(self, request, context):
        """
        Handles user login requests.

        Args:
            request (LoginUserRequest): The gRPC request containing `nickname` and `password`.
            context (grpc.ServicerContext): The gRPC context for handling metadata and status codes.

        Returns:
            LoginUserResponse: Response containing the JWT access token if successful.
        """
        try:
            user = self._find_user_by_nickname(request.nickname, context)

            if not user:
                context.set_code(GrpcError.NOT_FOUND.code)
                context.set_details("User not found.")
                return user_pb2.LoginUserResponse()

            return self._login_user_to_system(user, request, context)

        except Exception as e:
            context.set_code(GrpcError.INTERNAL)
            context.set_details(GrpcError.INTERNAL.format_message(str(e)))
            return user_pb2.LoginUserResponse()

    def _find_user_by_nickname(self, nickname, context):
        """
        Finds a user by nickname in the database.

        Args:
            nickname (str): The unique nickname of the user.
            context: The gRPC context for handling metadata and status codes.

        Returns:
            User:
                - The user object if found.
            None:
                - If no user with the given nickname exists.

        Raises:
            grpc.RpcError.NOT_FOUND:
                - If the user does not exist in the database.
        """
        with app.app_context():
            user = User.query.filter_by(nickname=nickname).first()

            if not user:
                context.set_code(GrpcError.USER_NOT_FOUND.code)
                context.set_details(GrpcError.USER_NOT_FOUND.message)
                return None

        return user

    def _build_collection_user_response(self, user, response_type):
        return response_type(
            id=user.id,
            name=user.name,
            about=user.about,
            nickname=user.nickname,
            profile_img_url=user.profile_img_url,
            followers=user.followers.count() if hasattr(user.followers, "count") else user.followers,
            following=user.following.count() if hasattr(user.following, "count") else user.following,
            member_since=user.member_since.strftime("%Y-%m-%d") if isinstance(user.member_since,
                                                                              datetime) else user.member_since,
        )

    def _build_user_response(self, user, response_type):
        return response_type(
            user=user_pb2.User(
                id=user.id,
                name=user.name,
                about=user.about,
                nickname=user.nickname,
                profile_img_url=user.profile_img_url,
                followers=user.followers.count() if hasattr(user.followers, "count") else user.followers,
                following=user.following.count() if hasattr(user.following, "count") else user.following,
                member_since=user.member_since.strftime("%Y-%m-%d") if isinstance(user.member_since,
                                                                                  datetime) else user.member_since,
            )
        )

    def _fetch_collection_users(self):
        with app.app_context():
            return User.query.all()

    def _fetch_user_by_id(self, user_id):
        return User.query.filter_by(id=user_id).first()

    def _create_user_in_db(self, request, context):
        """
        Creates a new user in the database.

        Args:
            request: The gRPC request containing the new user data.
            context: The gRPC context for handling metadata and status codes.

        Returns:
            User:
                - The newly created user object if the operation is successful.
            None:
                - If user creation fails due to:
                    - Invalid or missing request data.
                    - Required fields are missing.
                    - Nickname is already taken.
                    - Database commit failure.
                    - Unexpected internal server error.

        Raises:
            grpc.RpcError.INVALID_ARGUMENT:
                - If the request data is invalid or missing.
                - If required fields are missing or empty.

            grpc.RpcError.ALREADY_EXISTS:
                - If the provided nickname already exists in the database.

            grpc.RpcError.DATABASE_ERROR:
                - If a database error occurs during user creation.

            Exception:
                - If an unexpected internal error occurs.
        """
        try:
            with app.app_context():
                if not self._validate_data(request, context):
                    return None

                new_user_data = self._convert_grpc_response_to_dict(request)

                if not self._check_required_fields(new_user_data, context):
                    return None

                if not self._check_for_existing_nickname(new_user_data["nickname"], context):
                    return None

                hashed_password = self._hash_password(new_user_data["password"])
                new_user = self._create_user_instance(new_user_data, hashed_password)

                db.session.add(new_user)
                if not self._commit_session(context):
                    return None

                db.session.refresh(new_user)
                return new_user

        except Exception as e:
            context.set_code(GrpcError.INTERNAL.code)
            context.set_details(GrpcError.DATABASE_ERROR.format_message(str(e)))
            db.session.rollback()
            return None

    def _update_user_by_id(self, user, request, context):
        """
        Updates a user by ID in the database.

        Args:
            user: The user object to update.
            request: The gRPC request containing the new user data.
            context: The gRPC context for handling metadata and status codes.

        Returns:
            User: The updated user's data.
            None:
                - Given nickname already existing.
                - If current password does not math with hashed password.

        Raises:
            DatabaseError: If a database error occurs.
        """
        try:
            if not self._check_for_existing_nickname(request.nickname, context):
                return None

            new_hashed_password = self._check_valid_current_password_and_new_password(
                user, request.current_password, request.new_password, context
            )

            if not new_hashed_password:
                return None

            updated_data = self._update_user_instance(user, request, new_hashed_password)

            for key, value in updated_data.items():
                setattr(user, key, value)

            if not self._commit_session(context):
                return None

            db.session.refresh(user)
            return user

        except Exception as e:
            context.set_code(GrpcError.INTERNAL.code)
            context.set_details(GrpcError.DATABASE_ERROR.format_message(str(e)))
            db.session.rollback()
            return None

    def _delete_user_by_nickname(self, user, context):
        """
        Deletes a user by nickname in the database.

        Args:
            user: The user object to delete.
            context: The gRPC context for handling metadata and status codes.

        Returns:
            user_pb2.DeleteUserResponse:
                - A response indicating whether the deletion was successful or failed.
            None:
                - If the user could not be deleted due to a database error.

        Raises:
            grpc.RpcError:
                - `grpc.StatusCode.INTERNAL`: If a database error occurs during deletion.
        """
        try:
            with app.app_context():
                if user not in db.session:
                    user = db.session.merge(user)

                db.session.delete(user)
                if not self._commit_session(context):
                    return None

                return user_pb2.DeleteUserResponse(status="SUCCESS", message="User successfully deleted")

        except Exception as e:
            context.set_code(GrpcError.INTERNAL.code)
            context.set_details(GrpcError.DATABASE_ERROR.format_message(str(e)))
            db.session.rollback()
            return None

    def _commit_session(self, context):
        """
        Commits data to the database.

        Args:
            context: The gRPC context for handling metadata and status codes.

        Returns:
            bool:
                - `True` if the commit is successful.
                - `False` if a database error occurs.

        Raises:
            grpc.RpcError:
                - `grpc.StatusCode.INTERNAL`: If a database error occurs during the commit process.
        """
        try:
            db.session.commit()
            return True

        except SQLAlchemyError as db_error:
            db.session.rollback()
            context.set_code(GrpcError.DATABASE_ERROR.code)
            context.set_details(GrpcError.DATABASE_ERROR.format_message(str(db_error)))
            return False

    def _validate_data(self, request, context):
        """
        Validates the given gRPC request data.

        Args:
            request: The gRPC request containing the new user data.
            context: The gRPC context for handling metadata and status codes.

        Returns:
            dict:
                - The validated request data if valid.
                - `None` if the request is empty or contains invalid data.

        Raises:
            grpc.RpcError:
                - `grpc.StatusCode.INVALID_ARGUMENT`: If the request is empty or invalid.
        """
        try:
            if not request:
                context.set_code(GrpcError.INVALID_ARGUMENT.code)
                context.set_details("Request cannot be empty.")
                return None

            return request

        except Exception as e:
            context.set_code(GrpcError.INVALID_ARGUMENT.code)
            context.set_details(GrpcError.INVALID_ARGUMENT.format_message(str(e)))
            return None

    def _check_required_fields(self, data, context):
        """
        Checks for required fields in the given dictionary request.

        This function ensures that all required fields are present and not empty in the provided data.
        If any required field is missing or empty, it sets the appropriate gRPC error and returns `None`.

        Args:
            data (dict): The dictionary containing the required fields.
            context: The gRPC context for handling metadata and status codes.

        Returns:
            dict:
                - The validated data with required fields if all required fields are present.
                - `None` if any required field is missing or empty.

        Raises:
            grpc.RpcError:
                - `grpc.StatusCode.INVALID_ARGUMENT`: If any required field is missing or empty.
        """
        try:
            required_fields = ["nickname", "name", "password"]
            missing_fields = [field for field in required_fields if not data.get(field)]

            if missing_fields:
                context.set_code(GrpcError.INVALID_ARGUMENT.code)
                context.set_details(f"Missing or empty required fields: {', '.join(missing_fields)}")
                return None

            return data

        except Exception as e:
            context.set_code(GrpcError.INVALID_ARGUMENT.code)
            context.set_details(GrpcError.INVALID_ARGUMENT.format_message(str(e)))
            return None

    def _check_for_existing_nickname(self, nickname, context):
        """
        Checks whether the given nickname already exists in the database.

        Args:
            nickname (str): The nickname to check for uniqueness.
            context: The gRPC context for handling metadata and status codes.

        Returns:
            bool:
                - `False`: If the nickname is already taken.
                - `True`: If the nickname is available for use.
                - `None`: If an internal server error occurs.

        Raises:
            grpc.RpcError:
                - `grpc.StatusCode.ALREADY_EXISTS`: If the nickname is already in use.
                - `grpc.StatusCode.INTERNAL`: If an unexpected error occurs during execution.
        """
        try:
            with app.app_context():
                existing_user = db.session.query(User.query.filter_by(nickname=nickname).exists()).scalar()

                if existing_user:
                    context.set_code(GrpcError.ALREADY_EXISTS.code)
                    context.set_details("Nickname already taken.")
                    return False

                return True

        except Exception as e:
            context.set_code(GrpcError.INTERNAL.code)
            context.set_details(GrpcError.DATABASE_ERROR.format_message(str(e)))
            return None

    def _convert_grpc_response_to_dict(self, request):
        """
        Converts the given gRPC response to a dictionary.

        Args:
            request: The gRPC request containing the new user data.

        Returns:
            dict: The converted dictionary.
        """

        new_user_data = {
            field.name: getattr(request, field.name)
            for field in request.DESCRIPTOR.fields
        }

        return new_user_data

    def _create_user_instance(self, user_data, hashed_password):
        """
        Creates a new User instance from a dictionary of user data.

        Args:
            user_data (dict): The dictionary containing user attributes.
            hashed_password (str): The hashed password.

        Returns:
            User: A new User instance.
        """
        return User(
            name=user_data.get("name", ""),
            about=user_data.get("about", ""),
            nickname=user_data.get("nickname", ""),
            password=hashed_password,
            profile_img_url=user_data.get("profile_img_url", ""),
        )

    def _update_user_instance(self, user, request, new_hashed_password):
        """
        Creates a new User instance from a dictionary of user data.

        Args:
            user (dict): Current user data.
            request: The gRPC request containing the user new data.
            new_hashed_password (str): New password if it has been changed.

        Returns:
            dict: Converted user data to dictionary.
        """
        return {
            "name": request.name if request.name else user.name,
            "about": request.about if request.about else user.about,
            "nickname": request.nickname if request.nickname else user.nickname,
            "password": new_hashed_password if new_hashed_password else user.password,
            "profile_img_url": request.profile_img_url if request.profile_img_url else user.profile_img_url,
        }

    def _check_valid_current_password_and_new_password(self, user, current_password, new_password, context):
        """
        Validates the current password and hashes the new password if valid.

        Args:
            user (User): The user object.
            current_password (str): The current password provided by the user.
            new_password (str): The new password provided by the user.
            context: The gRPC context for handling metadata and status codes.

        Returns:
            str: The new hashed password if valid, otherwise the existing password.
            None: If the current password is incorrect.
        """
        if current_password and new_password:
            if not self._check_password(user, current_password, context):
                return None
            return self._hash_password(new_password)

        return user.password

    def _login_user_to_system(self, user, request, context):
        """
        Authenticates the user and generates an access token.

        Args:
            user (dict): User record retrieved from the database.
            request (LoginUserRequest): The gRPC request containing `nickname` and `password`.
            context (grpc.ServicerContext): The gRPC context for handling metadata and status codes.

        Returns:
            LoginUserResponse: Response containing the JWT access token if authentication is successful.
        """
        try:
            if not self._check_for_existing_nickname(request.nickname, context):
                return user_pb2.LoginUserResponse()

            validated = self._validate_login_data(request.nickname, request.password, context)
            if not validated:
                return user_pb2.LoginUserResponse()
            nickname, password = validated

            if not self._check_password(user, password, context):
                return user_pb2.LoginUserResponse()

            return user_pb2.LoginUserResponse()

        except Exception as e:
            context.set_code(GrpcError.INTERNAL.code)
            context.set_details(GrpcError.INTERNAL.format_message(str(e)))
            db.session.rollback()
            return user_pb2.LoginUserResponse()

    def _validate_login_data(self, nickname, password, context):
        """
        Validates login data and ensures both nickname and password are provided.

        Args:
            nickname (str): The user's nickname.
            password (str): The user's password.
            context (grpc.ServicerContext): The gRPC context used to set error codes and details.

        Returns:
            tuple: (nickname, password) if valid, otherwise None.

        Raises:
            GrpcError.INVALID_ARGUMENT: If nickname or password is missing.
        """
        try:
            if not nickname or not password:
                missing_fields = []
                if not nickname:
                    missing_fields.append("nickname")
                if not password:
                    missing_fields.append("password")

                error_message = f"Missing required fields: {', '.join(missing_fields)}."
                context.set_code(GrpcError.INVALID_ARGUMENT.code)
                context.set_details(GrpcError.INVALID_ARGUMENT.format_message(error_message))
                return None

            return nickname, password
        except Exception as e:
            context.set_code(GrpcError.INVALID_ARGUMENT.code)
            context.set_details(GrpcError.INVALID_ARGUMENT.format_message(str(e)))
            return None

    def _hash_password(self, password):
        """
        Hashes the given password.

        Args:
            password (str): The raw password.

        Returns:
            str: The hashed password.
        """
        return generate_password_hash(password)

    def _check_password(self, user, current_password, context):
        """
        Checks whether the given password matches the hashed password.

        Args:
            current_password (str): User's current password.
            user (dict): User's current data.
            context: The gRPC context for handling metadata and status codes.

        Returns:
            bool: True if the password matches the hashed password, otherwise False.
            None: If password does not match with the hashed password.

        Raises:
            grpc.RpcError:
                `grpc.StatusCode.INVALID_ARGUMENT`: If the given password does not match the hashed password.
        """
        if not user.check_password(current_password):
            context.set_code(GrpcError.INVALID_ARGUMENT.code)
            context.set_details(GrpcError.INVALID_ARGUMENT.format_message("Invalid password. Please try again."))
            return False

        return user.check_password(current_password)
