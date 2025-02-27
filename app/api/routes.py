from app.api.resources import *


def register_api_resources(api):
    """Register all RESTful resources"""
    api.add_resource(User, '/users/<string:nickname>')
    api.add_resource(UserUpdate, '/users/id/<int:user_id>')
    api.add_resource(UserList, '/users')

    api.add_resource(Register, '/register')
    api.add_resource(Login, '/login')
    api.add_resource(Logout, '/logout')
