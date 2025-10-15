from twilio.rest import Client

# Replace with your Twilio credentials
ACCOUNT_SID = "AC9abbd862265e09420c0b410c5f6c6d1d"
AUTH_TOKEN = "954f20ac6f9dd671dd4f25b74ae1e292"

# Replace with your Twilio phone number (must start with +)
TWILIO_NUMBER = "+18787788891"

def send_message(message, number):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    try:
        msg = client.messages.create(
            body=message,
            from_=TWILIO_NUMBER,
            to=number  # must be in E.164 format e.g. +639171234567
        )
        print(f"✅ Sent to {number} | SID: {msg.sid}")
    except Exception as e:
        print(f"❌ Failed to send to {number}: {e}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python send_sms_twilio.py 'Message here'")
    else:
        message = sys.argv[1]

        # Read all numbers from num.txt (one per line)
        try:
            with open("num.txt", "r") as f:
                numbers = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print("Error: num.txt not found.")
            sys.exit(1)

        print(f"📢 Sending to {len(numbers)} numbers via Twilio...")
        for number in numbers:
            send_message(message, number)
