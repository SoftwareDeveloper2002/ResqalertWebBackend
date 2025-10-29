from flask import Flask
from flask_cors import CORS
from report import report_bp
from dashboard import dashboard_bp
from login import login_bp  # Make sure this is defined in login.py
from sms import sms_bp  # Import the sms blueprint

app = Flask(__name__)

# CORS Configuration — allow all origins for /api/* routes
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    supports_credentials=True,
    methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)

# Register blueprints with correct prefixes
app.register_blueprint(report_bp, url_prefix='/api/report') # Enpoint for report blueprint
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard') # Endpoint for dashboard blueprint
app.register_blueprint(login_bp, url_prefix='/api/admin')  # This ensures endpoint is /api/admin/login
app.register_blueprint(sms_bp, url_prefix='/api/sms')  # Register sms blueprint

@app.route('/')
def home():
    return '✅ Flask backend for ResqAlert is running.'
    # This is the root endpoint
if __name__ == '__main__':
    app.run(debug=True, port=7000) # Main function
