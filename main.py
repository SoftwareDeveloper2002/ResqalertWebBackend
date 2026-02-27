from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix

from report import report_bp
from dashboard import dashboard_bp
from login import login_bp
from sms import sms_bp

app = Flask(__name__)

# Trust reverse proxy headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

# ===============================
# CORS Configuration
# ===============================
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    supports_credentials=True,
    methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)

# ===============================
# Register Blueprints
# ===============================
app.register_blueprint(report_bp, url_prefix='/api/report')
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
app.register_blueprint(login_bp, url_prefix='/api/admin')
app.register_blueprint(sms_bp, url_prefix='/api/sms')


# ===============================
# Root Endpoint
# ===============================
@app.route('/')
def home():
    ip = request.remote_addr
    user_agent = request.headers.get('User-Agent')
    referrer = request.referrer
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    print("\n===== VISITOR LOG =====")
    print(f"IP Address   : {ip}")
    print(f"User Agent   : {user_agent}")
    print(f"Referrer     : {referrer}")
    print(f"Access Time  : {timestamp}")
    print("========================\n")

    return render_template(
        'home.html',
        ip=ip,
        user_agent=user_agent,
        referrer=referrer,
        time=timestamp
    )


@app.route('/device-info', methods=['POST'])
def device_info():
    data = request.get_json()

    print("\n===== DEVICE INFO =====")
    print(f"Screen       : {data.get('screen')}")
    print(f"Platform     : {data.get('platform')}")
    print(f"Language     : {data.get('language')}")
    print("========================\n")

    return jsonify({"status": "received"}), 200


if __name__ == '__main__':
    app.run()