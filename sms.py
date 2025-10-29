from flask import Blueprint, request, jsonify
import requests
from datetime import datetime

sms_bp = Blueprint('sms', __name__)

FIREBASE_URL = 'https://resqalert-22692-default-rtdb.asia-southeast1.firebasedatabase.app'
SEMAPHORE_API = 'https://api.semaphore.co/api/v4/messages'
API_KEY = 'e266c4082f5edf3616afe87ed106b8dc'
SENDER_NAME = 'Resq'


def normalize_phone(number):
    """Normalize phone number to Semaphore format: 639XXXXXXXXX (no +)."""
    number = str(number).strip()
    if number.startswith("+63"):
        return number[1:]
    elif number.startswith("0"):
        return "63" + number[1:]
    elif number.startswith("63"):
        return number
    else:
        return "63" + number[-10:]


def send_sms(message, numbers):
    """
    Send SMS using Semaphore API via POST.
    numbers: str or list of phone numbers (will normalize automatically)
    """
    message = message.strip()
    if not message:
        print("Message is empty, not sending to:", numbers)
        return {'error': 'Message is empty'}

    if isinstance(numbers, list):
        numbers = ','.join([normalize_phone(n) for n in numbers])
    else:
        numbers = normalize_phone(numbers)

    payload = {
        'apikey': API_KEY,
        'number': numbers,
        'message': message,
        'sendername': SENDER_NAME
    }


    try:
        response = requests.post(SEMAPHORE_API, data=payload)
        response.raise_for_status()
        resp_json = response.json() if response.text else {}
        print("Semaphore response:", resp_json)

        if isinstance(resp_json, list) and resp_json:
            return {'status': resp_json[0].get("status", "Pending"), 'response': resp_json}
        elif isinstance(resp_json, dict):
            return {'status': resp_json.get("status", "Failed"), 'response': resp_json}
        else:
            return {'status': 'Failed', 'response': resp_json}
    except requests.exceptions.RequestException as e:
        return {'error': str(e)}


def write_alert_to_firebase(report_id, flag, phone, message, result):
    """Log SMS alert to Firebase Realtime Database."""
    semaphore_status = result.get("status", "Failed")
    status = "SENT" if semaphore_status in ["Sent", "Queued", "Pending"] else "FAILED"

    alert_data = {
        "report_id": report_id,
        "department": flag,
        "phone": phone,
        "message": message or result.get("response", {}).get("message", ""),
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    try:
        resp = requests.post(f"{FIREBASE_URL}/alerts.json", json=alert_data)
        resp.raise_for_status()
        print(f"Logged alert for {flag} in Firebase with status: {status}")
    except Exception as e:
        print(f"Failed to log alert: {e}")


@sms_bp.route('/send-sms', methods=['POST'])
def send_sms_endpoint():
    data = request.get_json()
    report_id = data.get('report_id')

    if not report_id:
        return jsonify({'error': 'Missing report_id'}), 400

    report_url = f"{FIREBASE_URL}/reports/{report_id}.json"
    report_resp = requests.get(report_url)
    report = report_resp.json() if report_resp.ok else None

    if not report:
        return jsonify({'error': 'Report not found'}), 404

    flags = report.get('flag', [])
    if not isinstance(flags, list):
        flags = [flags] if flags else []

    if not flags:
        return jsonify({'error': 'No department flags found'}), 400

    accident_type = report.get('accident_type') or "Emergency Incident"
    if isinstance(accident_type, list):
        accident_type = ", ".join(accident_type)

    latitude = report.get('latitude')
    longitude = report.get('longitude')

    location_info = "Unknown location"
    maps_link = None
    if latitude and longitude:
        location_info = f"Lat: {latitude}, Lng: {longitude}"
        maps_link = f"https://maps.google.com/?q={latitude},{longitude}"

    sent_to = []

    for flag in flags:
        admin_url = f"{FIREBASE_URL}/{flag}/admin1/phone.json"
        admin_resp = requests.get(admin_url)
        admin_phone = admin_resp.json() if admin_resp.ok else None

        if not admin_phone:
            print(f"No phone found for {flag}")
            continue

        message_lines = [
            f"{flag} ALERT",
            f"A {accident_type} has been reported!",
            f"Location: {location_info}",
            "",
            "Please RESPOND IMMEDIATELY to the area of emergency (accident, crime, or disaster).",
            "View the full report and details on the Resq Web Dashboard.",
        ]
        if maps_link:
            message_lines.append(f"Google Maps: {maps_link}")
        message_lines.append(f"Report ID: {report_id}")

        message = "\n".join(message_lines).strip()
        result = send_sms(message, admin_phone)
        write_alert_to_firebase(report_id, flag, admin_phone, message, result)
        sent_to.append({'department': flag, 'phone': admin_phone, 'message': message, 'result': result})

    return jsonify({'success': True, 'sent_to': sent_to})
