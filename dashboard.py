import os
import time
import requests
from flask import Blueprint, jsonify
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)
FIREBASE_URL = 'https://resqalert-22692-default-rtdb.asia-southeast1.firebasedatabase.app/reports.json'
GOOGLE_GEOCODE_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

# 🟢 Summary
@dashboard_bp.route('/api/dashboard/summary', methods=['GET'])
def dashboard_summary():
    try:
        res = requests.get(FIREBASE_URL)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        return jsonify({'error': 'Failed to fetch data', 'details': str(e)}), 500

    total = len(data)
    rescued = sum(1 for x in data.values() if x.get('status') == 'Rescued')
    invalid = sum(1 for x in data.values() if x.get('status') == 'Invalid')
    others = total - rescued - invalid

    return jsonify({
        'totalReports': total,
        'rescuedCount': rescued,
        'invalidCount': invalid,
        'otherCount': others
    })

# 🟡 Flags
@dashboard_bp.route('/api/dashboard/flags', methods=['GET'])
def flag_distribution():
    try:
        res = requests.get(FIREBASE_URL)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        return jsonify({'error': 'Failed to fetch flags', 'details': str(e)}), 500

    flag_counter = {}
    for item in data.values():
        flags = item.get('flag', [])
        for flag in flags:
            flag_counter[flag] = flag_counter.get(flag, 0) + 1

    return jsonify(flag_counter)

# 🔵 Monthly
@dashboard_bp.route('/api/dashboard/monthly', methods=['GET'])
def monthly_reports():
    try:
        res = requests.get(FIREBASE_URL)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        return jsonify({'error': 'Failed to fetch timeline data', 'details': str(e)}), 500

    report_count = {}
    for item in data.values():
        ts = item.get('timestamp')
        if ts:
            try:
                date = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                label = f"{date.strftime('%b')} {date.year}"
                report_count[label] = report_count.get(label, 0) + 1
            except Exception:
                continue

    return jsonify(report_count)

# 🟥 Barangay Stats
@dashboard_bp.route('/api/dashboard/barangay-stats', methods=['GET'])
def barangay_stats():
    if not GOOGLE_GEOCODE_API_KEY:
        return jsonify({'error': 'Missing Google Maps API Key'}), 500

    try:
        res = requests.get(FIREBASE_URL)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        return jsonify({'error': 'Failed to fetch reports', 'details': str(e)}), 500

    barangay_count = {}

    for item in data.values():
        lat = item.get('latitude')
        lng = item.get('longitude')

        if lat is None or lng is None:
            continue

        try:
            geo_url = (
                f'https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}'
                f'&key={GOOGLE_GEOCODE_API_KEY}'
            )
            geo_res = requests.get(geo_url)
            geo_data = geo_res.json()

            barangay_name = None

            if geo_data.get('status') == 'OK' and geo_data.get('results'):
                for result in geo_data['results']:
                    for comp in result.get('address_components', []):
                        if any(t in comp['types'] for t in ['sublocality_level_1', 'sublocality', 'neighborhood', 'political', 'locality']):
                            if 'Brgy' in comp['long_name'] or 'Barangay' in comp['long_name'] or len(comp['long_name'].split()) <= 3:
                                barangay_name = comp['long_name']
                                break
                    if barangay_name:
                        break

                # Fallback from formatted_address
                if not barangay_name:
                    formatted = geo_data['results'][0].get('formatted_address', '')
                    parts = [p.strip() for p in formatted.split(',')]
                    for part in parts:
                        if 'Barangay' in part or 'Brgy' in part:
                            barangay_name = part
                            break
                    if not barangay_name and parts:
                        barangay_name = parts[0]  # Absolute fallback

            barangay_name = barangay_name or 'Unknown'
            barangay_count[barangay_name] = barangay_count.get(barangay_name, 0) + 1

        except Exception as e:
            print(f"[Geocoding error] ({lat}, {lng}) -> {e}")
            continue

        time.sleep(0.1)  # Respect Google rate limits

    return jsonify(barangay_count)
