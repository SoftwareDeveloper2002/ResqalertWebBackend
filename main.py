from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
import json
import os
import requests

from report import report_bp
from dashboard import dashboard_bp
from login import login_bp
from sms import sms_bp

app = Flask(__name__)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vlogs.json")

def load_logs():
    if not os.path.exists(log_file):
        return []
    try:
        with open(log_file, "r") as f:
            return json.load(f)
    except:
        return []

def save_logs(data):
    logs = load_logs()
    logs.append(data)
    with open(log_file, "w") as f:
        json.dump(logs, f, indent=4)

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

def get_isp(ip):
    try:
        r = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        d = r.json()
        return {
            "isp": d.get("org", "unknown"),
            "city": d.get("city", "unknown"),
            "region": d.get("region", "unknown"),
            "country": d.get("country", "unknown"),
            "loc": d.get("loc", "unknown")
        }
    except:
        return {"isp": "unknown", "city": "unknown", "region": "unknown", "country": "unknown", "loc": "unknown"}

@app.route('/')
def home():
    ip = get_real_ip()
    user_agent = request.headers.get('User-Agent', 'Unknown')
    referrer = request.referrer or 'None'
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    isp_info = get_isp(ip)

    log = {
        "time": timestamp,
        "ip": ip,
        "isp": isp_info.get("isp"),
        "city": isp_info.get("city"),
        "region": isp_info.get("region"),
        "country": isp_info.get("country"),
        "user_agent": user_agent,
        "referrer": referrer
    }

    save_logs({"visitor": log})

    return render_template(
        'home.html',
        ip=ip,
        isp=isp_info.get("isp"),
        location=isp_info.get("city"),
        user_agent=user_agent,
        referrer=referrer,
        time=timestamp
    )

@app.route('/device-info', methods=['POST'])
def device_info():
    data = request.get_json(silent=True) or {}
    data["time"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    save_logs({"device_info": data})
    return jsonify({"status": "received"}), 200

@app.route('/view-shit')
def view_logs():
    return jsonify(load_logs())

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)