from flask import Blueprint, request, jsonify
import requests
import logging

login_bp = Blueprint('login', __name__)

FIREBASE_URL = 'https://resqalert-22692-default-rtdb.asia-southeast1.firebasedatabase.app'

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Optional: Define accepted roles
ALLOWED_ROLES = ['BFP', 'PNP', 'MDRRMO', 'SA']

@login_bp.route('/login', methods=['POST', 'OPTIONS'])
def admin_login():
    if request.method == 'OPTIONS':
        return '', 200

    data = request.get_json()

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', '').strip().upper()

    logger.debug(f"Login attempt - Username: {username}, Role: {role}")

    if not username or not password or not role:
        return jsonify({
            'success': False,
            'message': '❌ Missing username, password, or role'
        }), 400

    if role not in ALLOWED_ROLES:
        return jsonify({
            'success': False,
            'message': f'❌ Role {role} is not recognized.'
        }), 400

    try:
        # Firebase roles are stored in uppercase as you showed
        firebase_url = f"{FIREBASE_URL}/admins/{role}.json"
        logger.debug(f"Fetching from Firebase: {firebase_url}")
        response = requests.get(firebase_url)
        response.raise_for_status()

        users = response.json()
        logger.debug(f"Users for role {role}: {users}")

        if not users:
            return jsonify({
                'success': False,
                'message': f'❌ No users found for role {role}'
            }), 404 # Not found!

        for user_id, user_data in users.items():
            if (
                user_data.get('username', '').strip() == username and
                user_data.get('password', '').strip() == password
            ):
                logger.info(f"✅ Login successful for {username} as {role}")
                return jsonify({
                    'success': True,
                    'message': f'✅ Welcome, {username}',
                    'role': role
                }), 200 # Okay status return code

        return jsonify({
            'success': False,
            'message': '❌ Invalid username or password'
        }), 401 # Inavalid data

    except requests.exceptions.RequestException as e:
        logger.error(f"Firebase error: {e}")
        return jsonify({
            'success': False,
            'message': '❌ Firebase error',
            'error': str(e)
        }), 500 # Internal error server

