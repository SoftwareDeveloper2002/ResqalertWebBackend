from flask import Blueprint, request, jsonify
import requests

report_bp = Blueprint('report', __name__)

FIREBASE_URL = 'https://resqalert-22692-default-rtdb.asia-southeast1.firebasedatabase.app'
FCM_ENDPOINT = 'https://fcm.googleapis.com/fcm/send'
FCM_SERVER_KEY = 'Bearer YOUR_FCM_SERVER_KEY_HERE'  # 🔒 Replace with actual FCM key

# ⚠️ Replace these with actual FCM tokens for each department
device_tokens = {
    'PNP': 'fcm_token_pnp',
    'MDRRMO': 'fcm_token_mdrrmo',
    'BFP': 'fcm_token_bfp',
    'default': 'fcm_token_default'
}


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
    return requests.post(FCM_ENDPOINT, headers=headers, json=payload)


@report_bp.route('/api/reports/<item_id>/status', methods=['PATCH'])
def update_status(item_id):
    status = request.json.get('status')
    if status not in ['Responding', 'Rescued', 'Invalid']:
        return jsonify({'error': 'Invalid status'}), 400

    try:
        # 🔄 Update report status
        update_res = requests.patch(f'{FIREBASE_URL}/reports/{item_id}.json', json={'status': status})
        update_res.raise_for_status()

        # 📦 Get full report data
        report_res = requests.get(f'{FIREBASE_URL}/reports/{item_id}.json')
        report_res.raise_for_status()
        report_data = report_res.json()

        title = f"Report Status: {status}"
        body = f"The report '{item_id}' has been marked as '{status}'."

        flags = report_data.get('flag', [])
        lat = report_data.get('latitude')
        lng = report_data.get('longitude')
        location_link = get_google_maps_link(lat, lng) if lat and lng else None

        errors = []

        for dept in flags:
            token = device_tokens.get(dept, device_tokens['default'])
            notif_title = f"{dept} Alert - {status}"
            notif_body = f"{body}"
            if location_link:
                notif_body += f"\nLocation: {location_link}"

            fcm_res = send_fcm_notification(token, notif_title, notif_body)
            if fcm_res.status_code != 200:
                errors.append({dept: fcm_res.text})

        # 📝 Save to Firebase notifications
        notification_data = {
            'title': title,
            'message': body,
            'report_id': item_id,
            'status': status,
            'timestamp': report_data.get('timestamp'),
            'flags': flags
        }

        notif_log_res = requests.post(f'{FIREBASE_URL}/notifications.json', json=notification_data)
        notif_log_res.raise_for_status()

        if errors:
            return jsonify({'message': 'Status updated, some notifications failed', 'errors': errors}), 207

        return jsonify({'message': f"Status updated to '{status}' and notifications sent."}), 200

    except Exception as e:
        return jsonify({'error': 'Failed to update report or send notifications', 'details': str(e)}), 500


@report_bp.route('/api/reports', methods=['GET'])
def get_reports():
    role = request.args.get('role')  # Optional filter

    try:
        res = requests.get(f'{FIREBASE_URL}/reports.json')
        res.raise_for_status()
        data = res.json()

        if not data:
            return jsonify([]), 200

        # Convert dict to list
        reports = []
        for report_id, report in data.items():
            if isinstance(report, dict):
                report['id'] = report_id  # Add ID to each report
                reports.append(report)

        # Filter by role (department) if provided
        if role:
            reports = [
                report for report in reports
                if 'flag' in report and isinstance(report['flag'], list) and role in report['flag']
            ]

        return jsonify(reports), 200

    except Exception as e:
        return jsonify({'error': 'Failed to load reports', 'details': str(e)}), 500
