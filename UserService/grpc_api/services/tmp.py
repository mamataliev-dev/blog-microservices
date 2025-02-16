import grpc

from UserService.app.models import User
from UserService.grpc_api.messages import user_pb2, user_pb2_grpc
from UserService.app.extensions import db
from UserService.errors import GrpcError

from sqlalchemy.exc import SQLAlchemyError


class UserService(user_pb2_grpc.UserServiceServicer):
    """
    A gRPC service for managing user operations
    Provides methods to retrieve, create, update and delete
    a specific user and a collection of users
    """

    def GetUser(self, request, context):
        """
        Retrieves a specific user by nickname

        Args:
            request: The gRPC request containing the user nickname
            context: The gRPC context for handling metadata and status codes

        Returns:
            user_pb2.GetUserResponse: The user data if found

        Raises:
            grpc.StatusCode.NOT_FOUND: If the user does not exist
        """
        user = self._find_user_by_id(request.id, context)

        if not user:
            return user_pb2.GetUserResponse()

        return self._build_user_response(user, user_pb2.GetUserResponse)

    def GetCollectionUsers(self, request, context):
        """
        Retrieves a collection of users

        Args:
            request: The gRPC request (emty for this method)
            context: The gRPC context for handling metadata and status codes

        Returns:
            user_pb2.GetCollectionUsersResponse: The collection of users
        """
        users = self._fetch_collection_users()
        user_responses = [self._build_user_response(user, user_pb2.GetCollectionUsersResponse) for user in users]
        return user_pb2.GetCollectionUsersResponse(users=user_responses)

    def PostUpdateUser(self, request, context):
        """
        Updates a specific user by ID

        Args:
            request: The gRPC request containing the user data
            context: The gRPC context for handling metadata and status codes

        Returns:
            user_pb2.PostUpdateUserResponse: The updated user data
        """
        user = self._find_user_by_id(request.id, context)
        if not user:
            return user_pb2.PostUpdateUserResponse()

        updated_user = self._update_user_by_id(user, request, context)
        if not updated_user:
            return user_pb2.PostUpdateUserResponse()

        return self._build_updated_user_response(updated_user, user_pb2.PostUpdateUserResponse)

    def PosCreateUser(self, request, context):
        """
        Created a new user to database

        Args:
            request: The gRPC request containing the user data
            context: The gRPC context for handling metadata and status codes

        Returns:
            user_pb2.PosCreateUserResponse: The newly created user's data.
        """
        new_user = self._create_user_in_db(request, context)
        if not new_user:
            return user_pb2.PosCreateUserResponse()

        return self._build_user_response(new_user, user_pb2.PosCreateUserResponse)

    def PostDeleteUser(self, request, context):
        """
        Deletes a user by ID

        Args:
            request: The gRPC request containing the user's ID
            context: The gRPC context for handling metadata and status codes

        Returns:
            user_pb2.PostDeleteUserResponse: The deleted user's response
        """
        user = self._find_user_by_id(request.id, context)

        if not user:
            return user_pb2.PostDeleteUserResponse(status="FAILED")

        return self._delete_user_by_id(user, context)

    def _find_user_by_id(self, user_id, context):
        """
        Fetches a user from the database by their ID

        Args:
            user_id (int): The ID of the user to find
            context: The gRPC context for handling errors

        Returns:
            User: The user object if found, otherwise None
        """
        user = User.query.filter_by(id=user_id).first()

        if not user:
            context.set_code(GrpcError.USER_NOT_FOUND.code)
            context.set_details(GrpcError.USER_NOT_FOUND.message)
            return None
        return user

    def _build_user_response(self, user, response_type):
        """
        Converts a User object into the appropriate gRPC response type.

        Args:
            user (User): The user object to convert.
            response_type: The gRPC response class to use (GetUserResponse or PostUpdateUserResponse).

        Returns:
            A gRPC response containing user data.
        """
        return response_type(user=user_pb2.User(
            id=user.id,
            name=user.name,
            about=user.about,
            nickname=user.nickname,
            profile_img_url=user.profile_img_url,
            followers=user.followers,
            following=user.following,
            member_since=user.member_since,
        ))

    def _fetch_collection_users(self):
        """
        Fetches all users from the database

        Returns:
            list[User]: A list of all user objects
        """
        return User.query.all()

    def _update_user_by_id(self, user, request, context):
        """
        Update a user's details in the database.

        Args:
            user (User): The existing user object to update.
            request: The gRPC request containing the new data.
            context: The gRPC context for handling errors

        Returns:
            User: The updated user object.
        """
        try:
            update_data = {
                field.name: getattr(request, field.name)
                for field in request.DESCRIPTOR.fields
            }

            validated_data = self._validate_data(update_data, context)
            if validated_data is None:
                return None

            for key, value in validated_data.items():
                if value is not None:
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

    def _create_user_in_db(self, request, context):
        """
        Creates a new user in the database.

        Args:
            request: The gRPC request containing the new data.
            context: The gRPC context for handling errors.

        Returns:
            User: The newly created user object, or None if creation fails.
        """
        try:
            new_user_data = {
                field.name: getattr(request, field.name)
                for field in request.DESCRIPTOR.fields
            }

            validated_data = self._validate_data(new_user_data, context)
            if validated_data is None:
                return None

            new_user = User(
                name=validated_data["name"],
                about=validated_data.get("about"),
                nickname=validated_data["nickname"],
                profile_img_url=validated_data.get("profile_img_url"),
            )

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

    def _delete_user_by_id(self, user, context):
        """
        Deletes a user from the database by ID.

        Args:
            user: The user object to delete.

        Returns:
            user_pb2.PostDeleteUserResponse: The deleted user's response
        """
        try:
            db.session.delete(user)
            if not self._commit_session(context):
                return None

            db.session.refresh(user)
            return user_pb2.PostDeleteUserResponse(status="SUCCESS")

        except Exception as e:
            context.set_code(GrpcError.INTERNAL.code)
            context.set_details(GrpcError.DATABASE_ERROR.format_message(str(e)))
            db.session.rollback()
            return None

    def _commit_session(self, context):
        """
        Commits the database session and handles exceptions.
        Rolls back on failure and sets the gRPC error context.

        Args:
            context: The gRPC context for handling errors.

        Returns:
            bool: True if commit was successful, False otherwise.
        """
        try:
            db.session.commit()
            return True
        except SQLAlchemyError as db_error:
            db.session.rollback()
            context.set_code(GrpcError.DATABASE_ERROR.code)
            context.set_details(GrpcError.DATABASE_ERROR.format_message(str(db_error)))
            return False

    def _validate_data(self, data, context):
        """
        Validates the provided data.

        Args:
            data (dict): The data to validate.
            context: The gRPC context for handling errors.

        Returns:
            dict: The validated data if valid.
            None: If validation fails.
        """
        if not data:
            context.set_code(GrpcError.INVALID_ARGUMENT.code)
            context.set_details(GrpcError.INVALID_ARGUMENT.message)
            return None

        return data


"""
    def GetUser(self, request, context):
        with app.app_context():
            user = User.query.filter_by(id=request.id).first()
            if not user:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details("User not found")
                return user_pb2.UserResponse()

            return user_pb2.UserResponse(
                id=user.id,
                name=user.name,
                email=user.email
            )
"""
