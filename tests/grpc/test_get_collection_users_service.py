import grpc
import pytest
from grpc_api.services.user_service import UserService
from grpc_api.messages import user_pb2


class TestUserGetCollectionService:
    """
    Test suite for the `GetCollectionUsers` method in the User gRPC service.
    """

    def test_get_collection_users_success(self, mock_fetch_users, mock_service_build_user_response):
        """
        GIVEN a collection of users in the database
        WHEN a gRPC request is made to retrieve all users
        THEN it should return the list of users successfully.
        """
        fake_users = [
            user_pb2.User(id=1, name="John Doe", about="Software Engineer", nickname="johndoe",
                          profile_img_url="https://example.com/johndoe.jpg"),
            user_pb2.User(id=2, name="Jane Doe", about="Data Scientist", nickname="janedoe",
                          profile_img_url="https://example.com/janedoe.jpg"),
        ]

        mock_fetch_users.return_value = fake_users
        mock_service_build_user_response.side_effect = lambda user, _: user  # Simulating response conversion

        user_service = UserService()
        request = user_pb2.GetCollectionUsersRequest()
        response = user_service.GetCollectionUsers(request, context=None)

        assert len(response.users) == 2
        assert response.users[0].name == "John Doe"
        assert response.users[1].name == "Jane Doe"
        mock_fetch_users.assert_called_once()

    def test_get_collection_users_no_users_found(self, mock_fetch_users):
        """
        GIVEN an empty database
        WHEN a gRPC request is made to retrieve all users
        THEN it should return an empty response.
        """
        mock_fetch_users.return_value = []

        user_service = UserService()
        request = user_pb2.GetCollectionUsersRequest()
        response = user_service.GetCollectionUsers(request, context=None)

        assert len(response.users) == 0  # Ensuring empty response
        mock_fetch_users.assert_called_once()

    def test_get_collection_users_grpc_failure(self, mock_fetch_users):
        """
        GIVEN a gRPC failure
        WHEN a request is made to retrieve all users
        THEN it should return a 500 INTERNAL SERVER ERROR.
        """
        mock_fetch_users.side_effect = grpc.RpcError("gRPC server failure")

        user_service = UserService()
        request = user_pb2.GetCollectionUsersRequest()

        with pytest.raises(grpc.RpcError):
            user_service.GetCollectionUsers(request, context=None)

        mock_fetch_users.assert_called_once()
