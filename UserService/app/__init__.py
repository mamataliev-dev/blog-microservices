from flask import Flask
from .extensions import db, migrate, jwt


def create_app(config_class='config.DevelopmentConfig'):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # app.register_blueprint(api_blueprint, url_prefix='/api')

    return app