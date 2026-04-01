# app/__init__.py

import os

from flask import Flask
from flask_migrate import Migrate
import redis

from .conf.config import Config
from .model.models import db
from .monitoring import PrometheusMonitor
from .views_log import Log_bp
from .views_login import bcrypt, login_bp
from .views_equipment import Equipment_bp
from .views_order import Order_bp
from .views_tools import Tools_bp

app = None
migrate = Migrate()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    app.json.ensure_ascii = False

    os.makedirs(app.instance_path, exist_ok=True)

    monitor = PrometheusMonitor()
    monitor.init_app(app)

    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    app.redis = None
    if app.config.get("REDIS_ENABLED"):
        app.redis = redis.StrictRedis(
            host=app.config["REDIS_HOST"],
            port=app.config["REDIS_PORT"],
            db=app.config["REDIS_DB"],
            password=app.config["REDIS_PASSWORD"],
            decode_responses=app.config["REDIS_DECODE_RESPONSES"],
            socket_connect_timeout=1,
            socket_timeout=1,
        )

    with app.app_context():
        from .views_UserInfo import UserInfo_bp

        db.create_all()
        app.register_blueprint(UserInfo_bp, __name__="UserInfo_bp")

    app.register_blueprint(login_bp, __name__="login_bp")
    app.register_blueprint(Order_bp, __name__="Order_bp")
    app.register_blueprint(Equipment_bp, __name__="Equipment_bp")
    app.register_blueprint(Tools_bp, __name__="tools_bp")
    app.register_blueprint(Log_bp, __name__="log_bp")

    return app


def init_app(application):
    global app
    app = application
