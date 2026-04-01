from flask import Blueprint, Response
from prometheus_client import generate_latest

Log_bp = Blueprint('log_bp', __name__)


@Log_bp.route('/metrics/raw')
def metrics_endpoint():
    return Response(generate_latest(), mimetype='text/plain')
