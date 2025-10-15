import sys
import requests
import json
from datetime import datetime

API_KEY = "e266c4082f5edf3616afe87ed106b8dc"
SENDER_NAME = "SEMAPHORE"
LOG_FILE = "otp_log.json"

def send_otp(number, sender_name=SENDER_NAME, otp_length=6):
    url = "https://api.semaphore.co/api/v4/otp"

    payload = {
        "apikey": API_KEY,
        "number": number.strip(),
        "sendername": sender_name,
        "otp_length": otp_length,
        "otp_expiry": 300,
        "message": "Your OTP code is {{otp}}"
    }

    try:
        response = requests.post(url, data=payload)
        try:
            result = response.json()
        except Exception:
            result = {"error": "Invalid JSON response", "raw": response.text}

        # Handle list response
        if isinstance(result, list):
            first = result[0] if len(result) > 0 else {}
            status = "Sent" if first.get("success", False) else "Failed"
            otp_code = first.get("otp")
        else:
            status = "Sent" if result.get("success", False) else "Failed"
            otp_code = result.get("otp")

        if status == "Failed":
            print(f"❌ Failed to send OTP to {number}: {result}")

    except requests.RequestException as e:
        result = {"error": str(e)}
        status = "Failed"
        otp_code = None
        print(f"❌ Request exception for {number}: {e}")

    log_entry = {
        "message_id": result[0].get("message_id") if isinstance(result, list) and len(result) > 0 else result.get("message_id"),
        "user_id": None,
        "user": None,
        "account_id": None,
        "account": None,
        "recipient": number.strip(),
        "message": f"Your OTP code is {otp_code}" if otp_code else None,
        "code": otp_code,
        "sender_name": sender_name,
        "network": None,
        "status": status,
        "type": "OTP",
        "source": "Api",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "api_response": result
    }

    try:
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)
    except FileNotFoundError:
        logs = []

    logs.append(log_entry)

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)

    print(f"Number: {number} → Status: {status} | OTP: {otp_code}")
    return log_entry


if __name__ == "__main__":
    try:
        with open("num.txt", "r") as f:
            numbers = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("Error: num.txt not found.")
        sys.exit(1)

    print(f"📢 Sending OTPs to {len(numbers)} numbers...")

    for number in numbers:
        send_otp(number)
