from app.api.resources import *


def register_api_resources(api):
    """Register all RESTful resources"""
    api.add_resource(UserResource, '/users/<string:nickname>')
    api.add_resource(UserResourceById, '/users/id/<int:user_id>')
    api.add_resource(UserListResource, '/users')
