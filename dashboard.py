from flask import Blueprint, jsonify
import requests
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)
FIREBASE_URL = 'https://resqalert-22692-default-rtdb.asia-southeast1.firebasedatabase.app/reports.json'

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
