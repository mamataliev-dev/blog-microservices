import grpc
import pytest

from unittest.mock import MagicMock
from grpc_api.services.user_service import UserService
from grpc_api.messages import user_pb2


class TestUserUpdateService:
    """
    Test suite for the `UpdateUser` method in the User gRPC service.
    """

    def test_update_user_success(mock_user_query, mock_update_user_by_id, mock_service_build_user_response,
                                 mock_grpc_context):
        """
        GIVEN a valid user ID and update data
        WHEN a gRPC request is made to update the user
        THEN it should return the updated user details successfully.
        """
        fake_user = MagicMock()
        fake_user.id = 1
        fake_user.name = "Updated Name"
        fake_user.about = "Updated About"
        fake_user.nickname = "updatednickname"
        fake_user.profile_img_url = "https://example.com/updated.jpg"

        mock_user_query.filter_by.return_value.first.return_value = fake_user
        mock_update_user_by_id.return_value = fake_user
        mock_service_build_user_response.return_value = user_pb2.UpdateUserResponse(user=user_pb2.User(
            id=1,
            name="Updated Name",
            about="Updated About",
            nickname="updatednickname",
            profile_img_url="https://example.com/updated.jpg",
        ))

        user_service = UserService()
        request = user_pb2.UpdateUserRequest(
            id=1,
            name="Updated Name",
            about="Updated About",
            nickname="updatednickname",
            profile_img_url="https://example.com/updated.jpg",
        )
        response = user_service.UpdateUser(request, mock_grpc_context)

        assert response.user.id == 1
        assert response.user.name == "Updated Name"
        assert response.user.nickname == "updatednickname"
        mock_user_query.filter_by.assert_called_once_with(id=1)
        mock_update_user_by_id.assert_called_once()

    def test_update_user_not_found(self, mock_user_query):
        """
        GIVEN a user ID that does not exist
        WHEN a gRPC request is made to update the user
        THEN it should return an empty response.
        """
        mock_user_query.filter_by.return_value.first.return_value = None

        user_service = UserService()
        request = user_pb2.UpdateUserRequest(id=999)  # Non-existent user ID
        response = user_service.UpdateUser(request, context=None)

        assert response.user.id == 0  # Ensuring empty response
        assert response.user.name == ""
        assert response.user.nickname == ""
        mock_user_query.filter_by.assert_called_once_with(id=999)

    def test_update_user_grpc_failure(self, mock_user_query):
        """
        GIVEN a gRPC failure
        WHEN a request is made
        THEN it should raise a gRPC RpcError.
        """
        mock_user_query.filter_by.side_effect = grpc.RpcError("gRPC server failure")

        user_service = UserService()
        request = user_pb2.UpdateUserRequest(id=1, name="Updated Name")

        with pytest.raises(grpc.RpcError):
            user_service.UpdateUser(request, context=None)

        mock_user_query.filter_by.assert_called_once_with(id=1)
