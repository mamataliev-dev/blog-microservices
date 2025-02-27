from flask import Blueprint
from flask_restful import Api

from app.api.routes import register_api_resources

api_blueprint = Blueprint('api', __name__)
api = Api(api_blueprint)

register_api_resources(api)
