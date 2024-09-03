import datetime
import json
import os.path
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]
ORIGINAL_EVENTS_FILE = "secrets/original_events_full.json"


def save_original_event_data(events):
    original_event_data = []
    for event in events:
        original_event_data.append(
            {
                "id": event["id"],
                "summary": event.get("summary", "No Title"),
                "location": event.get("location"),
                "description": event.get("description"),
                "start": event["start"],
                "end": event["end"],
                "attendees": event.get("attendees"),
                "recurrence": event.get("recurrence"),
                "reminders": event.get("reminders"),
            }
        )
    with open(ORIGINAL_EVENTS_FILE, "w") as file:
        json.dump(original_event_data, file, indent=4)


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

        now = datetime.utcnow()
        today_start = datetime.combine(now, datetime.min.time()).isoformat() + "Z"
        today_end = datetime.combine(now, datetime.max.time()).isoformat() + "Z"
        midnight = datetime.combine(now + timedelta(days=1), datetime.min.time())

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=today_start,
                timeMax=today_end,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        # Save original event data
        save_original_event_data(events)

        total_available_time = (midnight - now).total_seconds()
        original_total_time = sum(
            [
                (
                    datetime.fromisoformat(event["end"]["dateTime"])
                    - datetime.fromisoformat(event["start"]["dateTime"])
                ).total_seconds()
                for event in events
            ]
        )

        if original_total_time > 0:
            for event in events:
                original_start = datetime.fromisoformat(event["start"]["dateTime"])
                original_end = datetime.fromisoformat(event["end"]["dateTime"])
                original_duration = (original_end - original_start).total_seconds()

                new_duration = (
                    original_duration / original_total_time
                ) * total_available_time
                new_start_time = now
                new_end_time = new_start_time + timedelta(seconds=new_duration)

                event["start"]["dateTime"] = new_start_time.isoformat() + "Z"
                event["end"]["dateTime"] = new_end_time.isoformat() + "Z"
                now = new_end_time

                updated_event = (
                    service.events()
                    .update(calendarId="primary", eventId=event["id"], body=event)
                    .execute()
                )
                print(f"Event updated: {updated_event.get('htmlLink')}")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
