from flask import Blueprint, request, jsonify
import requests

result_bp = Blueprint('result', __name__)

FIREBASE_URL = 'https://resqalert-22692-default-rtdb.asia-southeast1.firebasedatabase.app/reports'

def get_google_maps_link(lat, lng):
    return f'https://www.google.com/maps?q={lat},{lng}'

@result_bp.route('/api/reports', methods=['GET'])
def fetch_reports():
    role = request.args.get('role', 'Unknown')
    try:
        response = requests.get(f'{FIREBASE_URL}.json')
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return jsonify({'error': 'Unable to fetch reports', 'details': str(e)}), 500

    reports = []
    for key, entry in data.items():
        if isinstance(entry.get('flag'), list) and role in entry['flag']:
            lat = entry.get('latitude')
            lng = entry.get('longitude')
            report = {
                'id': key,
                **entry,
                'googleMapLink': get_google_maps_link(lat, lng) if lat and lng else None
            }
            reports.append(report)

    return jsonify(reports), 200

@result_bp.route('/api/reports/<item_id>/status', methods=['PATCH'])
def update_status(item_id):
    status = request.json.get('status')
    if status not in ['Responding', 'Rescued', 'Invalid']:
        return jsonify({'error': 'Invalid status'}), 400

    try:
        res = requests.patch(f'{FIREBASE_URL}/{item_id}.json', json={'status': status})
        res.raise_for_status()
    except Exception as e:
        return jsonify({'error': 'Status update failed', 'details': str(e)}), 500

    return jsonify({'message': f'Status updated to {status}'}), 200
