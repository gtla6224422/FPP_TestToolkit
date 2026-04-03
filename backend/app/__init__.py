import os
from pathlib import Path

import redis
from flask import Flask, send_from_directory
from flask_migrate import Migrate

from .conf.config import Config
from .model.models import db
from .monitoring import PrometheusMonitor
from .views_equipment import Equipment_bp
from .views_log import Log_bp
from .views_order import Order_bp
from .views_sql_kit import SqlKit_bp
from .views_testcase import Testcase_bp
from .views_tools import Tools_bp

app = None
migrate = Migrate()


def get_frontend_dist_dir(application: Flask) -> Path:
    return Path(application.root_path).parent.parent / "frontend" / "dist"


def create_app():
    application = Flask(
        __name__,
        instance_relative_config=True,
        static_folder=None,
        template_folder=None,
    )
    application.config.from_object(Config)
    application.json.ensure_ascii = False

    os.makedirs(application.instance_path, exist_ok=True)

    monitor = PrometheusMonitor()
    monitor.init_app(application)

    db.init_app(application)
    migrate.init_app(application, db)

    application.redis = None
    if application.config.get("REDIS_ENABLED"):
        application.redis = redis.StrictRedis(
            host=application.config["REDIS_HOST"],
            port=application.config["REDIS_PORT"],
            db=application.config["REDIS_DB"],
            password=application.config["REDIS_PASSWORD"],
            decode_responses=application.config["REDIS_DECODE_RESPONSES"],
            socket_connect_timeout=1,
            socket_timeout=1,
        )

    with application.app_context():
        from .views_UserInfo import UserInfo_bp

        db.create_all()
        application.register_blueprint(UserInfo_bp, __name__="UserInfo_bp")

    application.register_blueprint(Order_bp, __name__="Order_bp")
    application.register_blueprint(Equipment_bp, __name__="Equipment_bp")
    application.register_blueprint(Tools_bp, __name__="tools_bp")
    application.register_blueprint(Log_bp, __name__="log_bp")
    application.register_blueprint(SqlKit_bp, __name__="sql_kit_bp")
    application.register_blueprint(Testcase_bp, __name__="testcase_bp")

    @application.get("/")
    def root():
        frontend_dist_dir = get_frontend_dist_dir(application)
        if (frontend_dist_dir / "index.html").exists():
            return send_from_directory(frontend_dist_dir, "index.html")
        return {
            "status_code": 200,
            "message": "WebDemo Flask API is running",
            "data": {
                "available_prefixes": [
                    "/sql-kit/*",
                    "/testcases",
                    "/metrics",
                ]
            },
        }, 200

    @application.get("/assets/<path:filename>")
    def frontend_assets(filename: str):
        frontend_dist_dir = get_frontend_dist_dir(application)
        assets_dir = frontend_dist_dir / "assets"
        return send_from_directory(assets_dir, filename)

    @application.get("/<path:path>")
    def frontend_spa(path: str):
        frontend_dist_dir = get_frontend_dist_dir(application)
        target_path = frontend_dist_dir / path
        if target_path.exists() and target_path.is_file():
            return send_from_directory(frontend_dist_dir, path)
        if (frontend_dist_dir / "index.html").exists():
            return send_from_directory(frontend_dist_dir, "index.html")
        return {
            "status_code": 404,
            "error": f"路径不存在：/{path}",
        }, 404

    return application


def init_app(application):
    global app
    app = application
