import os
from datetime import timedelta


class Config:
    JWT_SECRET_KEY = os.getenv('SECRET_KEY', 'YOUR_SECRET_KEY')

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URI', 'postgresql://postgres:password@localhost:porst/blog'
    )


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True

    SQLALCHEMY_DATABASE_URI = os.getenv('TEST_DATABASE_URI', 'sqlite:///:memory:')


class ProductionConfig(Config):
    DEBUG = False

    SQLALCHEMY_DATABASE_URI = os.getenv(
        'PROD_DATABASE_URI', 'mysql+pymysql://root:password@localhost/prod_db'
    )
