from flask import Blueprint, request, jsonify
import requests
import logging

login_bp = Blueprint('login', __name__)  # DO NOT add url_prefix here

FIREBASE_URL = 'https://resqalert-22692-default-rtdb.asia-southeast1.firebasedatabase.app'

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@login_bp.route('/login', methods=['POST', 'OPTIONS'])  # Full route becomes /api/admin/login
def admin_login():
    if request.method == 'OPTIONS':
        return '', 200  # CORS preflight response

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

    try:
        firebase_url = f"{FIREBASE_URL}/admins/{role}.json"
        logger.debug(f"Fetching Firebase users from: {firebase_url}")
        response = requests.get(firebase_url)
        response.raise_for_status()

        users = response.json()
        logger.debug(f"Fetched users for role {role}: {users}")

        if not users:
            return jsonify({
                'success': False,
                'message': f'❌ No users found for role {role}'
            }), 404

        for user_id, user_data in users.items():
            u_name = user_data.get('username', '').strip()
            u_pass = user_data.get('password', '').strip()
            logger.debug(f"Checking: username={u_name}, password={u_pass}")

            if u_name == username and u_pass == password:
                logger.info(f"✅ Login successful for {username}")
                return jsonify({
                    'success': True,
                    'message': f'✅ Welcome, {username}',
                    'role': role
                }), 200

        return jsonify({
            'success': False,
            'message': '❌ Invalid username or password'
        }), 401

    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'message': '❌ Firebase error',
            'error': str(e)
        }), 500
