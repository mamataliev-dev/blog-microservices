import grpc

from grpc_api.messages import user_pb2


class TestUserPostAPI:
    """
    Test suite for the `post()` method in the User API.
    """

    def test_post_user_success(self, client, mock_create_user, mock_build_user_response):
        """
        GIVEN valid user data
        WHEN a POST request is made to create a user
        THEN it should return a 201 CREATED response with the created user data.
        """
        user_data = {
            "name": "John Doe",
            "about": "Software Engineer",
            "nickname": "johndoe",
            "profile_img_url": "https://example.com/johndoe.jpg",
        }

        fake_user_proto = user_pb2.CreateUserResponse(
            user=user_pb2.User(
                id=1,
                name="John Doe",
                about="Software Engineer",
                nickname="johndoe",
                profile_img_url="https://example.com/johndoe.jpg",
            )
        )
        mock_create_user.return_value = fake_user_proto
        mock_build_user_response.return_value = {"id": 1, "name": "John Doe", "nickname": "johndoe"}

        response = client.post('/users', json=user_data)

        assert response.status_code == 201
        assert response.json == {"id": 1, "name": "John Doe", "nickname": "johndoe"}
        mock_create_user.assert_called_once()

    def test_post_user_empty_request(self, client):
        """
        GIVEN an empty request body
        WHEN a POST request is made
        THEN it should return a 400 BAD REQUEST error.
        """
        response = client.post('/users', json={})  # Empty dictionary instead of None

        assert response.status_code == 400
        assert response.json == {"error": "Request body cannot be empty"}

    def test_post_user_grpc_failure(self, client, mock_create_user):
        """
        GIVEN a gRPC failure
        WHEN a POST request is made
        THEN it should return a 500 INTERNAL SERVER ERROR.
        """
        user_data = {
            "name": "John Doe",
            "about": "Software Engineer",
            "nickname": "johndoe",
            "profile_img_url": "https://example.com/johndoe.jpg",
        }

        mock_create_user.side_effect = grpc.RpcError("gRPC server failure")

        response = client.post('/users', json=user_data)

        assert response.status_code == 500
        assert "Unexpected gRPC error" in response.json["error"]
