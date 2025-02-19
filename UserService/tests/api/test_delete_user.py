import grpc

from grpc_api.messages import user_pb2


class TestUserDeleteAPI:
    """
    Test suite for the `delete()` method in the User API.
    """

    def test_delete_user_success(self, client, mock_delete_user):
        """
        GIVEN a valid nickname of an existing user
        WHEN a DELETE request is made to remove the user
        THEN it should return a 200 OK response with a success message.
        """
        fake_delete_response = user_pb2.DeleteUserResponse(status="SUCCESS", message="User successfully deleted")

        mock_delete_user.return_value = fake_delete_response

        response = client.delete('/users/johndoe')

        assert response.status_code == 200
        assert response.json == {"message": "User successfully deleted"}
        mock_delete_user.assert_called_once()

    def test_delete_user_not_found(self, client, mock_delete_user):
        """
        GIVEN a nickname that does not exist
        WHEN a DELETE request is made
        THEN it should return a 404 NOT FOUND error.
        """
        fake_delete_response = user_pb2.DeleteUserResponse(status="FAILED", message="User not found")

        mock_delete_user.return_value = fake_delete_response

        response = client.delete('/users/nonexistentuser')

        assert response.status_code == 404
        assert response.json == {"error": "User not found"}
        mock_delete_user.assert_called_once()

    def test_delete_user_grpc_failure(self, client, mock_delete_user):
        """
        GIVEN a gRPC failure
        WHEN a DELETE request is made
        THEN it should return a 500 INTERNAL SERVER ERROR.
        """
        mock_delete_user.side_effect = grpc.RpcError("gRPC server failure")

        response = client.delete('/users/johndoe')

        assert response.status_code == 500
        assert "Unexpected gRPC error" in response.json["error"]
