# coding=utf-8

import os

from app import create_app

# Flask 服务入口，支持本地运行和简单部署场景直接启动。
app = create_app()


if __name__ == '__main__':
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_RUN_PORT', '5003'))
    debug = os.getenv('FLASK_DEBUG', '').strip().lower() in {'1', 'true', 'yes', 'on'}
    app.run(host=host, port=port, debug=debug)
