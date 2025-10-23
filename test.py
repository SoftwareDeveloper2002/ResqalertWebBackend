import sys
import requests
apikey = 'e266c4082f5edf3616afe87ed106b8dc'
sendername = 'Resq'

def send_message(message, number):
    """Send an SMS message using the Semaphore API."""
    print("\nSending Message...")
    params = {
        'apikey': apikey,
        'sendername': sendername,
        'message': message,
        'number': number
    }
    try:
        response = requests.post("https://semaphore.co/api/v4/messages", data=params)
        response.raise_for_status()

        print("Message Sent Successfully!")
        print("Response:", response.json())
    except requests.exceptions.RequestException as e:
        print("Failed to send message.")
        print("Error:", e)
        if response is not None:
            print("Response:", response.text)

if __name__ == '__main__':
    if len(sys.argv) >= 3:
        message = sys.argv[1]
        number = sys.argv[2]
    else:
        print("No message or number provided as arguments.")
        message = input("Enter your message: ").strip()
        number = input("Enter recipient number (e.g. 09171234567): ").strip()

    if not message or not number:
        print("Message and number cannot be empty.")
        sys.exit(1)

    send_message(message, number)
