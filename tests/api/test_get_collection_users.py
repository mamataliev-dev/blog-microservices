import grpc

from grpc_api.messages import user_pb2


class TestUserGetAPI:
    """
    Test suite for the `get()` method in the User API.
    """

    def test_get_users_success(self, client, mock_get_all_users, mock_build_user_response):
        """
        GIVEN multiple users exist
        WHEN a GET request is made to retrieve all users
        THEN it should return a 200 OK response with the list of users.
        """
        fake_users_proto = user_pb2.GetCollectionUsersResponse(
            users=[
                user_pb2.User(
                    id=1,
                    name="John Doe",
                    about="Software Engineer",
                    nickname="johndoe",
                    profile_img_url="https://example.com/johndoe.jpg",
                ),
                user_pb2.User(
                    id=2,
                    name="Jane Doe",
                    about="Product Manager",
                    nickname="janedoe",
                    profile_img_url="https://example.com/janedoe.jpg",
                )
            ]
        )

        mock_get_all_users.return_value = fake_users_proto
        mock_build_user_response.side_effect = [
            {"id": 1, "name": "John Doe", "nickname": "johndoe"},
            {"id": 2, "name": "Jane Doe", "nickname": "janedoe"},
        ]

        response = client.get('/users')

        assert response.status_code == 200
        assert response.json == {
            "users": [
                {"id": 1, "name": "John Doe", "nickname": "johndoe"},
                {"id": 2, "name": "Jane Doe", "nickname": "janedoe"},
            ]
        }
        mock_get_all_users.assert_called_once()

    def test_get_users_empty_response(self, client, mock_get_all_users):
        """
        GIVEN no users exist
        WHEN a GET request is made
        THEN it should return a 200 OK response with an empty list.
        """
        fake_users_proto = user_pb2.GetCollectionUsersResponse(users=[])

        mock_get_all_users.return_value = fake_users_proto

        response = client.get('/users')

        assert response.status_code == 200
        assert response.json == {"users": []}
        mock_get_all_users.assert_called_once()

    def test_get_users_grpc_failure(self, client, mock_get_all_users):
        """
        GIVEN a gRPC failure
        WHEN a GET request is made
        THEN it should return a 500 INTERNAL SERVER ERROR.
        """
        mock_get_all_users.side_effect = grpc.RpcError("gRPC server failure")

        response = client.get('/users')

        assert response.status_code == 500
        assert "Unexpected gRPC error" in response.json["error"]
