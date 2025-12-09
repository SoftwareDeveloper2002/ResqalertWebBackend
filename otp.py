import requests
import random

# Configuration
SEMAPHORE_API_KEY = "e266c4082f5edf3616afe87ed106b8dc"  # Replace with your API key
SENDER_NAME = "Resq"
PHONE_NUMBER = "+639217017064"  # Replace with target phone number
USE_CUSTOM_OTP = True  # Set to False to let Semaphore generate OTP

# Generate OTP if needed
otp_code = f"{random.randint(0, 999999):06}" if USE_CUSTOM_OTP else None

# Message with {otp} placeholder
message = "Your ResqAlert OTP is: {otp}. Please use it within 5 minutes."

# Prepare payload
payload = {
    "apikey": SEMAPHORE_API_KEY,
    "number": PHONE_NUMBER,
    "message": message,
    "sendername": SENDER_NAME
}

if otp_code:
    payload["code"] = otp_code

# Send OTP
response = requests.post("https://api.semaphore.co/api/v4/otp", data=payload)

# Print response
if response.status_code in range(200, 300):
    print("OTP sent successfully!")
    print("Response:", response.json())
else:
    print("Failed to send OTP")
    print("Status code:", response.status_code)
    print("Response:", response.text)
