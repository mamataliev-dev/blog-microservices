import grpc
import pytest

from grpc_api.services.user_service import UserService
from grpc_api.messages import user_pb2


# mock_service_build_collection_user_response
class TestUserGetService:
    """
    Test suite for the `GetUser` method in the User gRPC service.
    """

    def test_get_user_success(self, mock_find_user, mock_service_build_collection_user_response):
        """
        GIVEN a valid nickname of an existing user
        WHEN a gRPC request is made to retrieve the user
        THEN it should return the user's details successfully.
        """
        fake_user = user_pb2.User(
            id=1,
            name="John Doe",
            about="Software Engineer",
            nickname="johndoe",
            profile_img_url="https://example.com/johndoe.jpg",
        )
        mock_find_user.return_value = fake_user
        mock_service_build_collection_user_response.return_value = user_pb2.GetUserResponse(user=fake_user)

        user_service = UserService()
        request = user_pb2.GetUserRequest(nickname="johndoe")
        response = user_service.GetUser(request, context=None)

        assert response.user.id == 1
        assert response.user.name == "John Doe"
        assert response.user.nickname == "johndoe"
        mock_find_user.assert_called_once()

    def test_get_user_not_found(self, mock_find_user):
        """
        GIVEN a nickname that does not exist
        WHEN a gRPC request is made to retrieve the user
        THEN it should return an empty response.
        """
        mock_find_user.return_value = None

        user_service = UserService()
        request = user_pb2.GetUserRequest(nickname="nonexistentuser")
        response = user_service.GetUser(request, context=None)

        assert response.user.id == 0  # Ensuring empty response
        assert response.user.name == ""
        assert response.user.nickname == ""
        mock_find_user.assert_called_once()

    def test_get_user_grpc_failure(self, mock_find_user):
        """
        GIVEN a gRPC failure
        WHEN a request is made
        THEN it should return a 500 INTERNAL SERVER ERROR.
        """
        mock_find_user.side_effect = grpc.RpcError("gRPC server failure")

        user_service = UserService()
        request = user_pb2.GetUserRequest(nickname="johndoe")

        with pytest.raises(grpc.RpcError):
            user_service.GetUser(request, context=None)

        mock_find_user.assert_called_once()
