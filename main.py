from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
import os

from report import report_bp
from dashboard import dashboard_bp
from login import login_bp
from sms import sms_bp

app = Flask(__name__)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

script_dir = os.path.dirname(os.path.abspath(__file__))
log_file_path = os.path.join(script_dir, "vlogs.txt")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

if logger.handlers:
    logger.handlers = []

file_handler = logging.FileHandler(log_file_path)
stream_handler = logging.StreamHandler()

formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    supports_credentials=True,
    methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)

app.register_blueprint(report_bp, url_prefix='/api/report')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(login_bp, url_prefix='/api/admin')
app.register_blueprint(sms_bp, url_prefix='/api/sms')


def get_real_ip():
    if request.headers.get("CF-Connecting-IP"):
        return request.headers.get("CF-Connecting-IP")

    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()

    if request.headers.get("X-Real-IP"):
        return request.headers.get("X-Real-IP")

    return request.remote_addr


@app.route('/')
def home():
    ip = get_real_ip()
    user_agent = request.headers.get('User-Agent', 'Unknown')
    referrer = request.referrer or 'None'
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    logger.info(
        "VISITOR LOG | IP: %s | UA: %s | REF: %s | TIME: %s",
        ip, user_agent, referrer, timestamp
    )

    return render_template(
        'home.html',
        ip=ip,
        user_agent=user_agent,
        referrer=referrer,
        time=timestamp
    )


@app.route('/device-info', methods=['POST'])
def device_info():
    data = request.get_json(silent=True) or {}

    logger.info(
        "DEVICE INFO | Screen: %s | Platform: %s | Language: %s | Connection: %s | Downlink: %s | RTT: %s",
        data.get("screen"),
        data.get("platform"),
        data.get("language"),
        data.get("connection"),
        data.get("downlink"),
        data.get("rtt")
    )

    return jsonify({"status": "received"}), 200


@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)