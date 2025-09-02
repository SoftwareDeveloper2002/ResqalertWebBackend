from flask import Blueprint, request, jsonify
import requests as http_requests
import time

# ==============================
# 🔹 Report & Request Blueprint
# ==============================
report_bp = Blueprint('report_bp', __name__)

FIREBASE_URL = 'https://resqalert-22692-default-rtdb.asia-southeast1.firebasedatabase.app'
FCM_ENDPOINT = 'https://fcm.googleapis.com/fcm/send'
FCM_SERVER_KEY = 'Bearer YOUR_FCM_SERVER_KEY_HERE'  # 🔒 Replace with actual FCM key

# 🔐 Replace with real FCM tokens for each department
device_tokens = {
    'PNP': 'fcm_token_pnp',
    'MDRRMO': 'fcm_token_mdrrmo',
    'BFP': 'fcm_token_bfp',
    'default': 'fcm_token_default'
}

# ====================================
# 🔧 Utility functions
# ====================================
def get_google_maps_link(lat, lng):
    return f'https://www.google.com/maps?q={lat},{lng}'


def send_fcm_notification(token, title, body):
    headers = {
        'Authorization': FCM_SERVER_KEY,
        'Content-Type': 'application/json'
    }
    payload = {
        'to': token,
        'notification': {
            'title': title,
            'body': body,
            'sound': 'default'
        },
        'priority': 'high'
    }
    return http_requests.post(FCM_ENDPOINT, headers=headers, json=payload)


# ====================================
# 📌 Report Endpoints
# ====================================

# ✅ PATCH: Update report status
@report_bp.route('/reports/<item_id>/status', methods=['PATCH'])
def update_status(item_id):
    status = request.json.get('status')
    if status not in ['Responding', 'Rescued', 'Invalid']:
        return jsonify({'error': 'Invalid status'}), 400

    try:
        update_res = http_requests.patch(f'{FIREBASE_URL}/reports/{item_id}.json', json={'status': status})
        update_res.raise_for_status()

        report_res = http_requests.get(f'{FIREBASE_URL}/reports/{item_id}.json')
        report_res.raise_for_status()
        report_data = report_res.json()

        title = f"Report Status: {status}"
        body = f"The report '{item_id}' has been marked as '{status}'."

        flags = report_data.get('flag', [])
        lat = report_data.get('latitude')
        lng = report_data.get('longitude')
        location_link = get_google_maps_link(lat, lng) if lat and lng else None

        errors = []
        if not isinstance(flags, list):
            flags = [flags] if flags else []

        for dept in flags:
            token = device_tokens.get(dept, device_tokens['default'])
            notif_title = f"{dept} Alert - {status}"
            notif_body = body
            if location_link:
                notif_body += f"\nLocation: {location_link}"

            fcm_res = send_fcm_notification(token, notif_title, notif_body)
            if fcm_res.status_code != 200:
                errors.append({dept: fcm_res.text})

        # Save notification log
        notification_data = {
            'title': title,
            'message': body,
            'report_id': item_id,
            'status': status,
            'timestamp': report_data.get('timestamp'),
            'flags': flags
        }
        http_requests.post(f'{FIREBASE_URL}/notifications.json', json=notification_data)

        if errors:
            return jsonify({'message': 'Status updated, some notifications failed', 'errors': errors}), 207

        return jsonify({'message': f"Status updated to '{status}' and notifications sent."}), 200

    except Exception as e:
        return jsonify({'error': 'Failed to update report or send notifications', 'details': str(e)}), 500


# ✅ GET all reports
@report_bp.route('/reports', methods=['GET'])
def get_reports():
    role = request.args.get('role')

    try:
        res = http_requests.get(f'{FIREBASE_URL}/reports.json')
        res.raise_for_status()
        data = res.json()

        if not data:
            return jsonify([]), 200

        reports = []
        for report_id, report in data.items():
            if isinstance(report, dict):
                report['id'] = report_id
                reports.append(report)

        if role:
            role = role.upper()
            reports = [
                report for report in reports
                if 'flag' in report and (
                    (isinstance(report['flag'], list) and role in [f.upper() for f in report['flag']]) or
                    (isinstance(report['flag'], str) and report['flag'].upper() == role)
                )
            ]

        return jsonify(reports), 200

    except Exception as e:
        return jsonify({'error': 'Failed to load reports', 'details': str(e)}), 500


# ✅ GET report by ID (numeric index or Firebase ID)
@report_bp.route('/reports/<item_id>', methods=['GET'])
def get_report_by_id(item_id):
    try:
        if item_id.isdigit():
            res = http_requests.get(f'{FIREBASE_URL}/reports.json')
            res.raise_for_status()
            reports = res.json() or {}

            if not reports:
                return jsonify({'error': 'No reports found'}), 404

            sorted_reports = sorted(
                reports.items(),
                key=lambda kv: kv[1].get('timestamp', 0)
            )

            index = int(item_id) - 1
            if index < 0 or index >= len(sorted_reports):
                return jsonify({'error': 'Report not found'}), 404

            report_id, report_data = sorted_reports[index]
            report_data['id'] = report_id
            return jsonify(report_data), 200

        else:
            res = http_requests.get(f'{FIREBASE_URL}/reports/{item_id}.json')
            res.raise_for_status()
            report = res.json()

            if not report:
                return jsonify({'error': 'Report not found'}), 404

            report['id'] = item_id
            return jsonify(report), 200

    except Exception as e:
        return jsonify({'error': 'Failed to load report', 'details': str(e)}), 500


# ====================================
# 📌 Request Endpoints
# ====================================

# ✅ Create a new request entry
@report_bp.route('/requests', methods=['POST', 'OPTIONS'])
def create_request():
    if request.method == "OPTIONS":  # Handle preflight
        return jsonify({}), 200

    try:
        data = request.json
        if not data:
            return jsonify({"error": "Missing request body"}), 400

        incident_id = data.get("incident_id")
        from_role = data.get("from_role")
        to_role = data.get("to_role")

        if not incident_id or not from_role or not to_role:
            return jsonify({"error": "Both 'incident_id' and 'role' are required"}), 400

        request_entry = {
            "incident_id": incident_id,
            "from_role": data.get("from_role", "").upper(),  # role making the request
            "to_role": data.get("to_role", "").upper(),      # target role / department
            "status": "Pending",
            "timestamp": int(time.time() * 1000)
        }

        res = http_requests.post(f"{FIREBASE_URL}/requests.json", json=request_entry)
        res.raise_for_status()

        return jsonify({
            "message": "Request created successfully",
            "request_id": res.json()["name"],
            "data": request_entry
        }), 201

    except Exception as e:
        return jsonify({"error": "Failed to create request", "details": str(e)}), 500

# ✅ Get requests for current role
@report_bp.route('/requests', methods=['GET'])
def get_requests_for_role():
    current_role = request.args.get("role")
    if not current_role:
        return jsonify({"error": "role query parameter is required"}), 400

    try:
        # Fetch all requests
        res = http_requests.get(f"{FIREBASE_URL}/requests.json")
        res.raise_for_status()
        data = res.json() or {}

        # Filter requests where to_role matches current role
        filtered_requests = []
        for req_id, req in data.items():
            if isinstance(req, dict) and req.get("to_role", "").upper() == current_role.upper():
                req["id"] = req_id  # include Firebase key
                filtered_requests.append(req)

        return jsonify(filtered_requests), 200

    except Exception as e:
        return jsonify({"error": "Failed to fetch requests", "details": str(e)}), 500


# ✅ Accept request (update status to Approved)
@report_bp.route('/requests/<request_id>/approve', methods=['PATCH'])
def approve_request(request_id):
    try:
        update_data = {"status": "Approved", "approved_timestamp": int(time.time() * 1000)}

        # Update the request in Firebase
        res = http_requests.patch(f"{FIREBASE_URL}/requests/{request_id}.json", json=update_data)
        res.raise_for_status()

        return jsonify({"message": "Request approved successfully", "updated_data": update_data}), 200

    except Exception as e:
        return jsonify({"error": "Failed to approve request", "details": str(e)}), 500
