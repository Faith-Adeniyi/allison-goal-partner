import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# The specific permission level we are requesting from the user's vault
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# Root level paths since uvicorn runs from the main directory
CREDENTIALS_PATH = 'credentials.json'
TOKEN_PATH = 'token.json'

def get_calendar_service():
    """
    Handles the secure OAuth 2.0 handshake with Google Cloud.
    Generates a persistent token so the user only logs in once.
    """
    creds = ""
    
    # Check if we already have an active ID badge saved
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        
    # If the badge is invalid, missing, or expired, we request a new one
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # This triggers the browser popup for the user to grant permission
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the new ID badge for future background executions
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    # Build and return the authorized calendar client
    service = build('calendar', 'v3', credentials=creds)
    return service

def create_calendar_event(title: str, start_datetime: str, description: str = "") -> str:
    """
    CRITICAL INSTRUCTIONS FOR AI:
    - title: MUST be dynamically generated based on the user's specific goal and task. NEVER use generic test titles like 'Systems Check'.
    - start_datetime: MUST be strictly formatted as an ISO 8601 string (YYYY-MM-DDTHH:MM:SS).
    - description: MUST be a short, highly motivating summary of the task. 
    """
    try:
        service = get_calendar_service()
        
        start_time = datetime.datetime.fromisoformat(start_datetime)
        end_time = start_time + datetime.timedelta(hours=1)
        
        event_body = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'Africa/Lagos', 
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'Africa/Lagos',
            },
        }

        event_result = service.events().insert(calendarId='primary', body=event_body).execute()
        return f"Success! Event created: {event_result.get('htmlLink')}"
        
    except Exception as e:
        return f"Failed to access calendar: {str(e)}"

# --- STANDALONE TEST BLOCK ---
if __name__ == '__main__':
    print("Initiating Google Calendar OAuth Handshake...")
    # Creates a test event for tomorrow at 10:00 AM
    tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).replace(hour=10, minute=0, second=0)
    
    test_event_title = "Allison Agent: Systems Check"
    test_event_desc = "Verifying MCP tool calling capabilities."
    
    result = create_calendar_event(
        title=test_event_title, 
        start_datetime=tomorrow.isoformat(), 
        description=test_event_desc
    )
    print(result)