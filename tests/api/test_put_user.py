import grpc

from grpc_api.messages import user_pb2


class TestUserPutAPI:
    """
    Test suite for the `put()` method in the User API.
    """

    def test_put_user_success(self, client, mock_update_user, mock_build_user_response):
        """
        GIVEN valid user data
        WHEN a PUT request is made to update a user
        THEN it should return a 200 OK response with the updated user data.
        """
        user_data = {
            "name": "Updated Name",
            "about": "Updated About",
            "nickname": "updatednickname",
            "profile_img_url": "https://example.com/updated.jpg",
        }

        fake_user_proto = user_pb2.UpdateUserResponse(
            user=user_pb2.User(
                id=1,
                name="Updated Name",
                about="Updated About",
                nickname="updatednickname",
                profile_img_url="https://example.com/updated.jpg",
            )
        )
        mock_update_user.return_value = fake_user_proto
        mock_build_user_response.return_value = {"id": 1, "name": "Updated Name", "nickname": "updatednickname"}

        response = client.put('/users/id/1', json=user_data, content_type="application/json")

        assert response.status_code == 200
        assert response.json == {"id": 1, "name": "Updated Name", "nickname": "updatednickname"}
        mock_update_user.assert_called_once()

    def test_put_user_empty_request(self, client):
        """
        GIVEN an empty request body
        WHEN a PUT request is made
        THEN it should return a 400 BAD REQUEST error.
        """
        response = client.put('/users/id/1', json={},
                              content_type="application/json")

        assert response.status_code == 400
        assert response.json == {"error": "Request body cannot be empty"}

    def test_put_user_grpc_failure(self, client, mock_update_user):
        """
        GIVEN a gRPC failure
        WHEN a PUT request is made
        THEN it should return a 500 INTERNAL SERVER ERROR.
        """
        user_data = {
            "name": "Updated Name",
            "about": "Updated About",
            "nickname": "updatednickname",
            "profile_img_url": "https://example.com/updated.jpg",
        }

        mock_update_user.side_effect = grpc.RpcError("gRPC server failure")

        response = client.put('/users/id/1', json=user_data, content_type="application/json")

        assert response.status_code == 500
        assert "Unexpected gRPC error" in response.json["error"]
