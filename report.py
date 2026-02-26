from flask import Blueprint, request, jsonify, send_file
import requests as http_requests
import time
import os
import traceback
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

report_bp = Blueprint('report_bp', __name__)

# Firebase & FCM configuration
FIREBASE_URL = 'https://resqalert-22692-default-rtdb.asia-southeast1.firebasedatabase.app'
FCM_ENDPOINT = 'https://fcm.googleapis.com/fcm/send'
FCM_SERVER_KEY = 'Bearer YOUR_FCM_SERVER_KEY_HERE'

device_tokens = {
    'PNP': 'fcm_token_pnp',
    'MDRRMO': 'fcm_token_mdrrmo',
    'BFP': 'fcm_token_bfp',
    'default': 'fcm_token_default'
}

UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# Utility functions
def get_google_maps_link(lat, lng):
    return f'https://www.google.com/maps?q={lat},{lng}'


def send_fcm_notification(token, title, body):
    headers = {'Authorization': FCM_SERVER_KEY, 'Content-Type': 'application/json'}
    payload = {'to': token, 'notification': {'title': title, 'body': body, 'sound': 'default'}, 'priority': 'high'}
    return http_requests.post(FCM_ENDPOINT, headers=headers, json=payload)


def generate_pdf(report_data):
    pdf_file = os.path.join(UPLOAD_FOLDER, f"report_{report_data.get('incident_id', 'unknown')}.pdf")
    c = canvas.Canvas(pdf_file, pagesize=letter)
    width, height = letter
    y = height - 40

    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Incident / Accident Report")
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(50, y, "Generated Report")
    y -= 15
    c.drawString(50, y, f"Date/Time: {datetime.now().strftime('%m/%d/%Y, %I:%M:%S %p')}")
    y -= 15

    # Report metadata
    for key in ["from_role", "place_name", "latitude", "longitude", "status", "accident_type"]:
        c.drawString(50, y, f"{key.replace('_', ' ').title()}: {report_data.get(key, 'N/A')}")
        y -= 15

    # People involved
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "People Involved")
    y -= 15
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Who's Involved: {report_data.get('whoInvolved', 'N/A')}")
    y -= 15
    c.drawString(50, y, f"No. of People: {report_data.get('peopleCount', 'N/A')}")
    y -= 20

    # Additional notes
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Additional Notes")
    y -= 15
    c.setFont("Helvetica", 10)
    c.drawString(50, y, report_data.get('notes', 'No notes provided.'))
    y -= 20

    # Incident details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Incident Details")
    y -= 15
    c.setFont("Helvetica", 10)
    c.drawString(50, y, report_data.get('details', 'No additional details provided.'))
    y -= 30

    # Images
    images = report_data.get('images', [])
    for img_path in images:
        if os.path.exists(img_path):
            try:
                img_height = 150
                if y - img_height < 50:
                    c.showPage()
                    y = height - 50
                c.drawImage(img_path, 50, y - img_height, width=200, height=img_height, preserveAspectRatio=True)
                y -= img_height + 10
            except Exception:
                print(f"Failed to add image {img_path}: {Exception}")

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, 30, "This report was sysasdtem generated.")
    c.save()
    return pdf_file


# Routes
@report_bp.route('/reports/<item_id>/status', methods=['PATCH'])
def update_status(item_id):
    status = request.json.get('status')
    if status not in ['During', 'After', 'Invalid']:
        return jsonify({'error': 'Invalid status'}), 400
    try:
        http_requests.patch(f'{FIREBASE_URL}/reports/{item_id}.json', json={'status': status}).raise_for_status()
        report_data = http_requests.get(f'{FIREBASE_URL}/reports/{item_id}.json').json()
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
            notif_body = body + (f"\nLocation: {location_link}" if location_link else "")
            fcm_res = send_fcm_notification(token, notif_title, notif_body)
            if fcm_res.status_code != 200:
                errors.append({dept: fcm_res.text})

        # Save notification to Firebase
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


@report_bp.route('/reports', methods=['GET'])
def get_reports():
    role = request.args.get('role')
    try:
        data = http_requests.get(f'{FIREBASE_URL}/reports.json').json()
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


@report_bp.route('/reports/<item_id>', methods=['GET'])
def get_report_by_id(item_id):
    try:
        role = request.args.get('role')
        reports = http_requests.get(f'{FIREBASE_URL}/reports.json').json() or {}
        if not reports:
            return jsonify({'error': 'No reports found'}), 404
        if role:
            reports = {k: v for k, v in reports.items() if role in v.get('flag', [])}
        if not reports:
            return jsonify({'error': f'No reports found for role {role}'}), 404

        sorted_reports = sorted(reports.items(), key=lambda kv: kv[1].get('timestamp', 0))
        if item_id.isdigit():
            index = int(item_id) - 1
            if index < 0 or index >= len(sorted_reports):
                return jsonify({'error': f'Report at index {item_id} not found for role {role}'}), 404
            report_id, report_data = sorted_reports[index]
        else:
            report_id, report_data = next(((k, v) for k, v in reports.items() if k == item_id), (None, None))
            if not report_data:
                return jsonify({'error': 'Report not found'}), 404

        report_data['id'] = report_id
        return jsonify(report_data), 200
    except Exception as e:
        return jsonify({'error': 'Failed to load report', 'details': str(e)}), 500


# Request routes
@report_bp.route('/requests', methods=['POST', 'OPTIONS'])
def create_request():
    if request.method == "OPTIONS":
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
            "from_role": from_role.upper(),
            "to_role": to_role.upper(),
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


@report_bp.route('/requests', methods=['GET'])
def get_requests_for_role():
    current_role = request.args.get("role")
    if not current_role:
        return jsonify({"error": "role query parameter is required"}), 400
    try:
        data = http_requests.get(f"{FIREBASE_URL}/requests.json").json() or {}
        filtered_requests = []
        for req_id, req in data.items():
            if isinstance(req, dict) and (
                req.get("to_role", "").upper() == current_role.upper() or
                req.get("from_role", "").upper() == current_role.upper()
            ):
                req["id"] = req_id
                filtered_requests.append(req)
        return jsonify(filtered_requests), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch requests", "details": str(e)}), 500


@report_bp.route('/requests/<request_id>/approve', methods=['PATCH', 'OPTIONS'])
def approve_request(request_id):
    if request.method == "OPTIONS":
        return jsonify({}), 200
    try:
        update_data = {"status": "Approved", "approved_timestamp": int(time.time() * 1000)}
        http_requests.patch(f"{FIREBASE_URL}/requests/{request_id}.json", json=update_data).raise_for_status()
        return jsonify({"message": "Request approved successfully", "updated_data": update_data}), 200
    except Exception as e:
        return jsonify({"error": "Failed to approve request", "details": str(e)}), 500


@report_bp.route('/requests/<request_id>/decline', methods=['PATCH', 'OPTIONS'])
def decline_request(request_id):
    if request.method == "OPTIONS":
        return jsonify({}), 200
    try:
        update_data = {"status": "Rejected", "declined_timestamp": int(time.time() * 1000)}
        http_requests.patch(f"{FIREBASE_URL}/requests/{request_id}.json", json=update_data).raise_for_status()
        return jsonify({"message": "Request declined successfully", "updated_data": update_data}), 200
    except Exception as e:
        return jsonify({"error": "Failed to decline request", "details": str(e)}), 500


@report_bp.route('/request_data', methods=['POST', 'OPTIONS', 'GET'])
def request_data():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    if request.method == "POST":
        try:
            data = request.get_json() or request.form.to_dict()

            if not data:
                return jsonify({"error": "Missing request body"}), 400

            data['whoInvolved'] = data.get('whoInvolved') or 'N/A'
            data['peopleCount'] = int(data.get('peopleCount') or 0)
            data['details'] = data.get('details') or 'No additional details provided.'
            data['notes'] = data.get('notes') or 'No notes provided.'
            data['incident_id'] = data.get('incident_id') or 'N/A'
            data['from_role'] = data.get('from_role') or 'N/A'
            data['to_role'] = data.get('to_role') or 'N/A'
            data['status'] = data.get('status') or 'Pending'
            data['timestamp'] = int(data.get('timestamp') or time.time() * 1000)

            res = http_requests.post(
                f"{FIREBASE_URL}/request_data.json",
                json=data
            )
            res.raise_for_status()

            return jsonify({
                "message": "Saved successfully",
                "firebase_id": res.json().get("name"),
                "data": data
            }), 201

        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": "Failed to save request_data", "details": str(e)}), 500

    if request.method == "GET":
        try:
            data = http_requests.get(f"{FIREBASE_URL}/request_data.json").json() or {}
            request_list = [{"id": k, **v} for k, v in data.items()]
            return jsonify(request_list), 200

        except Exception as e:
            traceback.print_exc()
            return jsonify({"error": "Failed to fetch request_data", "details": str(e)}), 500

@report_bp.route('/reports/<item_id>/pdf', methods=['GET'])
def download_report_pdf(item_id):
    try:
        # 1️⃣ Get all request_data entries
        all_requests = http_requests.get(
            f'{FIREBASE_URL}/request_data.json'
        ).json() or {}

        # 2️⃣ Find latest request matching this incident_id
        matching_requests = [
            v for v in all_requests.values()
            if v.get('incident_id') == item_id
        ]

        if not matching_requests:
            return jsonify({"error": "No request_data found for this incident"}), 404

        # Sort by timestamp descending
        latest_request = sorted(
            matching_requests,
            key=lambda x: x.get('timestamp', 0),
            reverse=True
        )[0]

        # 3️⃣ Generate PDF using EDITED DATA
        pdf_file = generate_pdf(latest_request)

        return send_file(
            pdf_file,
            as_attachment=True,
            download_name=f'report_{item_id}.pdf'
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": "Failed to generate PDF",
            "details": str(e)
        }), 500


@report_bp.route('/reports/<item_id>', methods=['PATCH'])
def patch_report(item_id):
    try:
        data = request.json or {}

        # update firebase report
        http_requests.patch(
            f'{FIREBASE_URL}/reports/{item_id}.json',
            json=data
        ).raise_for_status()

        return jsonify({"message": "Report updated"}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": "Failed to update report",
            "details": str(e)
        }), 500