import grpc

from app.models import User
from app.extensions import db
from errors import GrpcError
from grpc_api.messages import user_pb2, user_pb2_grpc

from sqlalchemy.exc import SQLAlchemyError


class UserService(user_pb2_grpc.UserServiceServicer):
    """
    A gRPC service for managing user operations
    Provides methods to retrieve, create, update, and delete
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
            UserNotFound: If the user not found
        """
        user = self._find_user_by_nickname(request.nickname, context)

        if not user:
            return user_pb2.GetUserResponse()

        return self._build_user_response(user, user_pb2.GetUserResponse)

    def GetCollectionUsers(self, request, context):
        """
        Retrieves a collection of users

        Args:
            request: The gRPC request (empty for this method)
            context: The gRPC context for handling metadata and status codes

        Returns:
            user_pb2.GetCollectionUsersResponse: The collection of users
        """
        users = self._fetch_collection_users()
        user_responses = [self._build_user_response(user, user_pb2.GetCollectionUsersResponse) for user in users]
        return user_pb2.GetCollectionUsersResponse(users=user_responses)

    def UpdateUser(self, request, context):
        """
        Updates a specific user by nickname

        Args:
            request: The gRPC request containing the user new data
            context: The gRPC context for handling metadata and status codes

        Returns:
            user_pb2.PostUpdateUserResponse: The updated user data

        Raises:
            UserNotFound: If the user not found
        """
        user = self._find_user_by_nickname(request.nickname, context)
        if not user:
            return user_pb2.UpdateUserResponse()

        updated_user = self._update_user_by_nickname(user, request, context)

        return self._build_updated_user_response(updated_user, user_pb2.UpdateUserResponse)

    def CreateUser(self, request, context):
        """
        Creates a new user in the database

        Args:
            request: The gRPC request containing the user data
            context: The gRPC context for handling metadata and status codes

        Returns:
            user_pb2.CreateUserResponse: The newly created user's data.
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
        Deletes a user by nickname

        Args:
            request: The gRPC request containing the user's nickname
            context: The gRPC context for handling metadata and status codes

        Returns:
            user_pb2.PostDeleteUserResponse: The deleted user's response (FAILED or SUCCESS)
        """
        user = self._find_user_by_nickname(request.nickname, context)

        if not user:
            return user_pb2.DeleteUserResponse(status="FAILED", message="User not found")

        return self._delete_user_by_nickname(user, context)

    def _find_user_by_nickname(self, nickname, context):
        """
        Finds a user by nickname in the database.

        Args:
            nickname (str): The unique nickname of the user.
            context: The gRPC context for handling metadata and status codes.

        Returns:
            User: The user object if found

        Raises:
            grpc.StatusCode.NOT_FOUND: If the user does not exist.
        """
        user = User.query.filter_by(nickname=nickname).first()

        if not user:
            context.set_code(GrpcError.USER_NOT_FOUND.code)
            context.set_details(GrpcError.USER_NOT_FOUND.message)
            return None

        return user

    def _build_user_response(self, user, response_type):
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
        return User.query.all()

    def _create_user_in_db(self, request, context):
        """
        Creates a new user in the database.

        Args:
            request: The gRPC request containing the new user data
            context: The gRPC context for handling metadata and status codes

        Returns:
            User: The newly created user's data.

        Raises:
            DatabaseError: If database errors occurs
        """
        try:
            new_user_data = {
                field.name: getattr(request, field.name)
                for field in request.DESCRIPTOR.fields
            }

            new_user = User(
                name=new_user_data["name"],
                about=new_user_data["about"],
                nickname=new_user_data["nickname"],
                profile_img_url=new_user_data["profile_img_url"],
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

    def _update_user_by_nickname(self, user, request, context):
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

    def _delete_user_by_nickname(self, user, context):
        """
        Deletes a user by nickname in the database.

        Args:
            user: The user object to delete.
            context: The gRPC context for handling metadata and status codes.

        Returns:
            user_pb2.PostDeleteUserResponse: The deleted user's response (FAILED or SUCCESS)

        Raises:
            DatabaseError: If database errors occurs.
        """
        try:
            db.session.delete(user)
            if not self._commit_session(context):
                return None

            db.session.refresh(user)
            return user_pb2.DeleteUserResponse(status="SUCCESS", message="User successfully deleted")

        except Exception as e:
            context.set_code(GrpcError.INTERNAL.code)
            context.set_details(GrpcError.DATABASE_ERROR.format_message(str(e)))
            db.session.rollback()
            return None

    def _commit_session(self, context):
        try:
            db.session.commit()
            return True

        except SQLAlchemyError as db_error:
            db.session.rollback()
            context.set_code(GrpcError.DATABASE_ERROR.code)
            context.set_details(GrpcError.DATABASE_ERROR.format_message(str(db_error)))
            return False
