import pytest

from flask import Flask
from unittest.mock import patch
from unittest.mock import MagicMock

from grpc_api.services.user_service import UserService
from app.api.resources import UserListResource, UserResourceById, UserResource


@pytest.fixture
def app():
    """
    Creates and configures a new Flask app instance for testing.
    """
    app = Flask(__name__)
    app.testing = True

    app.add_url_rule('/users/<string:nickname>', view_func=UserResource.as_view('user_resource'))
    app.add_url_rule('/users', view_func=UserListResource.as_view('user_list_resource'))
    app.add_url_rule('/users/id/<int:user_id>', view_func=UserResourceById.as_view('user_resource_by_id'))

    return app


@pytest.fixture
def client(app):
    """
    Creates a test client for making HTTP requests.
    """
    return app.test_client()


@pytest.fixture
def mock_create_user():
    """
    Mocks the gRPC CreateUser method.
    """
    with patch("app.api.resources.user.stub.CreateUser") as mock_create_user:
        yield mock_create_user


@pytest.fixture
def mock_update_user():
    """
    Mocks the gRPC UpdateUser method.
    """
    with patch("app.api.resources.user.stub.UpdateUser") as mock_update_user:
        yield mock_update_user


@pytest.fixture
def mock_get_all_users():
    """
    Mocks the gRPC GetCollectionUsers method.
    """
    with patch("app.api.resources.user.stub.GetCollectionUsers") as mock_get_all_users:
        yield mock_get_all_users


@pytest.fixture
def mock_delete_user():
    """
    Mocks the gRPC DeleteUser method.
    """
    with patch("app.api.resources.user.stub.DeleteUser") as mock_delete_user:
        yield mock_delete_user


@pytest.fixture
def mock_build_user_response():
    """
    Mocks the `_build_user_response()` method.
    """
    with patch("app.api.resources.user.UserResource._build_user_response") as mock_response:
        yield mock_response


@pytest.fixture
def mock_find_user():
    """
    Mocks the `_find_user_by_nickname()` method.
    """
    with patch.object(UserService, "_find_user_by_nickname") as mock:
        yield mock


@pytest.fixture
def mock_service_build_user_response():
    """
    Mocks the `_build_user_response()` method.
    """
    with patch.object(UserService, "_build_user_response") as mock:
        yield mock


@pytest.fixture
def mock_service_build_collection_user_response():
    """
    Mocks the `_build_collection_user_response()` method.
    """
    with patch.object(UserService, "_build_collection_user_response") as mock:
        yield mock


@pytest.fixture
def mock_fetch_users():
    """
    Mocks the `_fetch_collection_users()` method.
    """
    with patch.object(UserService, "_fetch_collection_users") as mock:
        yield mock


@pytest.fixture
def mock_user_query(app):
    """
    Mocks the User.query.filter_by(id=request.id).first() call.
    """
    with app.app_context():
        with patch("app.models.User.query") as mock_query:
            yield mock_query


@pytest.fixture
def mock_update_user_by_id():
    """
    Mocks the method that updates a user by their ID.
    """
    with patch("grpc_api.services.user_service.UserService._update_user_by_id") as mock:
        yield mock


@pytest.fixture
def mock_grpc_context():
    """
    Mocks the gRPC context for handling metadata and status codes.
    """
    mock_context = MagicMock()
    return mock_context
