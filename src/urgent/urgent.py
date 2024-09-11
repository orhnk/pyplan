import datetime
import os.path
import random

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]

COLORS = {
    "1": "Lavender",
    "2": "Sage",
    "3": "Grape",
    "4": "Flamingo",
    "5": "Banana",
    "6": "Tangerine",
    "7": "Peacock",
    "8": "Graphite",
    "9": "Blueberry",
    "10": "Basil",
    "11": "Tomato",
}


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

        # Get user inputs
        summary = input("Enter the task summary: ")
        duration_minutes = int(input("Enter the duration of the task in minutes: "))
        color_choice = input(
            "Enter the color ID (1-11) or type 'random' for a random color: "
        ).strip()

        if color_choice.lower() == "random":
            color_id = str(random.choice(list(COLORS.keys())))
        else:
            color_id = color_choice

        if color_id not in COLORS:
            print("Invalid color choice. Defaulting to color ID 1 (Lavender).")
            color_id = "1"

        # Calculate new event's duration in seconds
        new_event_duration = datetime.timedelta(
            minutes=duration_minutes
        ).total_seconds()

        # Fetch events for the current day
        now = datetime.datetime.now(datetime.UTC)
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + datetime.timedelta(days=1)

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_of_day.isoformat(),
                timeMax=end_of_day.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        # Calculate total duration of existing events in seconds
        total_duration = 0
        for event in events:
            start_time = datetime.datetime.fromisoformat(
                event["start"]
                .get("dateTime", event["start"].get("date"))
                .replace("Z", "+00:00")
            )
            end_time = datetime.datetime.fromisoformat(
                event["end"]
                .get("dateTime", event["end"].get("date"))
                .replace("Z", "+00:00")
            )
            event_duration = (end_time - start_time).total_seconds()
            total_duration += event_duration

        # If there are no events, just insert the new event at the start of the day
        if not events:
            start_time = now
            end_time = now + datetime.timedelta(minutes=duration_minutes)
            create_event(service, summary, start_time, end_time, color_id)
            print(f"Event created: {event.get('htmlLink')}")
            return

        # Calculate new duration for each existing event
        for event in events:
            start_time = datetime.datetime.fromisoformat(
                event["start"]
                .get("dateTime", event["start"].get("date"))
                .replace("Z", "+00:00")
            )
            end_time = datetime.datetime.fromisoformat(
                event["end"]
                .get("dateTime", event["end"].get("date"))
                .replace("Z", "+00:00")
            )
            event_duration = (end_time - start_time).total_seconds()

            # Calculate new duration proportionally
            new_event_duration = event_duration / total_duration * new_event_duration
            new_end_time = start_time + datetime.timedelta(seconds=new_event_duration)

            # Debugging output to trace the error
            print(f"Updating event: {event['summary']} (ID: {event['id']})")
            print(f"Original End Time: {end_time}")
            print(f"New End Time: {new_end_time}")

            # Update the event with the new duration
            event["end"]["dateTime"] = new_end_time.isoformat() + "Z"
            service.events().update(
                calendarId="primary", eventId=event["id"], body=event
            ).execute()

        # Find the first available time slot to insert the new event
        available_start = events[-1]["end"][
            "dateTime"
        ]  # After the last event of the day
        available_start = datetime.datetime.fromisoformat(
            available_start.replace("Z", "+00:00")
        )
        new_event_start = available_start
        new_event_end = new_event_start + datetime.timedelta(minutes=duration_minutes)

        # Create the new event
        create_event(service, summary, new_event_start, new_event_end, color_id)

    except HttpError as error:
        print(f"An error occurred: {error}")


def create_event(service, summary, start_time, end_time, color_id):
    """Creates a new event in the Google Calendar."""
    event = {
        "summary": summary,
        "start": {
            "dateTime": start_time.isoformat() + "Z",
            "timeZone": "UTC",
        },
        "end": {
            "dateTime": end_time.isoformat() + "Z",
            "timeZone": "UTC",
        },
        "colorId": color_id,
    }

    event = service.events().insert(calendarId="primary", body=event).execute()
    print(f"Event created: {event.get('htmlLink')}")


if __name__ == "__main__":
    main()
