from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
import logging

from report import report_bp
from dashboard import dashboard_bp
from login import login_bp
from sms import sms_bp

# =====================================================
# Initialize App
# =====================================================
app = Flask(__name__)

# =====================================================
# TRUST REVERSE PROXIES (AWS ALB / Nginx / Cloudflare)
# =====================================================
# x_for=1 → trust first proxy (ALB or Nginx)
# x_proto=1 → trust X-Forwarded-Proto (http/https)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# =====================================================
# Logging Configuration (Production Friendly)
# =====================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# =====================================================
# CORS Configuration
# =====================================================
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    supports_credentials=True,
    methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)

# =====================================================
# Register Blueprints
# =====================================================
app.register_blueprint(report_bp, url_prefix='/api/report')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(login_bp, url_prefix='/api/admin')
app.register_blueprint(sms_bp, url_prefix='/api/sms')

# =====================================================
# Helper: Get Real Client IP
# =====================================================
def get_real_ip():
    """
    Works with:
    - AWS ALB
    - Nginx
    - Cloudflare
    - Direct connections
    """
    if request.headers.get('CF-Connecting-IP'):
        return request.headers.get('CF-Connecting-IP')

    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()

    return request.remote_addr


# =====================================================
# Root Endpoint
# =====================================================
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

    return render_template(
        'home.html',
        ip=ip,
        user_agent=user_agent,
        referrer=referrer,
        time=timestamp
    )


# =====================================================
# Collect Extra Device Info
# =====================================================
@app.route('/device-info', methods=['POST'])
def device_info():
    data = request.get_json(silent=True) or {}

    logging.info("===== DEVICE INFO =====")
    logging.info(f"Screen    : {data.get('screen')}")
    logging.info(f"Platform  : {data.get('platform')}")
    logging.info(f"Language  : {data.get('language')}")
    logging.info("========================")

    return jsonify({
        "status": "received",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }), 200


# =====================================================
# Health Check (Useful for AWS ALB)
# =====================================================
@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200


# =====================================================
# Run Application (For EC2 Direct Run)
# =====================================================
if __name__ == '__main__':
    # Use 0.0.0.0 so EC2 accepts external traffic
    app.run(host='0.0.0.0', port=8000)