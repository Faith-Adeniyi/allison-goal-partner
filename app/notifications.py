from exponent_server_sdk import (
    DeviceNotRegisteredError,
    PushClient,
    PushMessage,
    PushServerError,
)
from requests.exceptions import ConnectionError, HTTPError

def send_push_notification(token, title, message, extra=None):
    try:
        response = PushClient().publish(
            PushMessage(to=token,
                        title=title,
                        body=message,
                        data=extra))
    except (ConnectionError, HTTPError) as exc:
        # Encountered some Connection or HTTP error - retry a few times in real app
        print(f"Failed to send notification: {exc}")
        
    try:
        # We got a response back, but we don't know whether it's an error yet
        if response.status != "ok":
            print(f"Notification failed: {response.message}")
            if response.details.get("error") == "DeviceNotRegistered":
                # Mark the token as inactive in your DB here
                pass
    except (ValueError, Exception) as exc:
        print(f"Invalid response: {exc}")