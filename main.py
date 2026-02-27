from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
import logging

from report import report_bp
from dashboard import dashboard_bp
from login import login_bp
from sms import sms_bp

app = Flask(__name__)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

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
    if request.headers.get('CF-Connecting-IP'):
        return request.headers.get('CF-Connecting-IP')
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return request.remote_addr

@app.route('/')
def home():
    ip = get_real_ip()
    user_agent = request.headers.get('User-Agent', 'Unknown')
    referrer = request.referrer or 'None'
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    logging.info("===== VISITOR LOG =====")
    logging.info(f"IP Address  : {ip}")
    logging.info(f"User Agent  : {user_agent}")
    logging.info(f"Referrer    : {referrer}")
    logging.info(f"Access Time : {timestamp}")
    logging.info("========================")

    return render_template('home.html', ip=ip, user_agent=user_agent, referrer=referrer, time=timestamp)

@app.route('/device-info', methods=['POST'])
def device_info():
    data = request.get_json(silent=True) or {}

    logging.info("===== DEVICE INFO =====")
    logging.info(f"Screen    : {data.get('screen')}")
    logging.info(f"Platform  : {data.get('platform')}")
    logging.info(f"Language  : {data.get('language')}")
    logging.info("========================")

    return jsonify({"status": "received", "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}), 200

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)