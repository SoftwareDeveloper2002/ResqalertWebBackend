from flask import Flask
from flask_cors import CORS
from result import result_bp
from dashboard import dashboard_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(result_bp)
app.register_blueprint(dashboard_bp)

@app.route('/')
def home():
    return 'Flask backend for ResqAlert is running.'

if __name__ == '__main__':
    app.run(debug=True, port=7000)
