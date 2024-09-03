import os.path
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]
ORIGINAL_EVENTS_FILE = "secrets/original_events_full.json"

def load_original_event_data():
    if os.path.exists(ORIGINAL_EVENTS_FILE):
        with open(ORIGINAL_EVENTS_FILE, "r") as file:
            return json.load(file)
    else:
        print("No original events file found.")
        return []

def main():
    creds = None
    if os.path.exists("secrets/cal-token.json"):
        creds = Credentials.from_authorized_user_file("secrets/cal-token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "secrets/credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("secrets/cal-token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        # Load original event data
        original_events = load_original_event_data()

        if not original_events:
            print("No original events found to restore.")
            return

        for original_event in original_events:
            event_id = original_event['id']
            restored_event = {
                "summary": original_event['summary'],
                "location": original_event['location'],
                "description": original_event['description'],
                "start": original_event['start'],
                "end": original_event['end'],
                "attendees": original_event['attendees'],
                "recurrence": original_event['recurrence'],
                "reminders": original_event['reminders'],
            }

            updated_event = service.events().update(
                calendarId="primary", eventId=event_id, body=restored_event
            ).execute()
            print(f"Event restored: {updated_event.get('htmlLink')}")

    except Http
