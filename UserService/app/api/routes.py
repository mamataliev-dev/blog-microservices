from app.api.resources import *


def register_api_resources(api):
    """Register all RESTful resources"""
    api.add_resource(UserResource, '/users/<string:user_nickname>')
    api.add_resource(UserListResource, '/users')
