import datetime
import os.path

from dateutil import parser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_events_for_date(service, date):
    """Fetch events for a specific date."""
    date_start = (
        datetime.datetime.combine(date, datetime.time.min)
        .replace(tzinfo=datetime.timezone.utc)
        .isoformat()
    )
    date_end = (
        datetime.datetime.combine(date, datetime.time.max)
        .replace(tzinfo=datetime.timezone.utc)
        .isoformat()
    )

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=date_start,
            timeMax=date_end,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return events_result.get("items", [])


def delete_events_for_date(service, target_date):
    """Delete all events for a specified date."""
    target_start = (
        datetime.datetime.combine(target_date, datetime.time.min)
        .replace(tzinfo=datetime.timezone.utc)
        .isoformat()
    )
    target_end = (
        datetime.datetime.combine(target_date, datetime.time.max)
        .replace(tzinfo=datetime.timezone.utc)
        .isoformat()
    )

    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=target_start,
            timeMax=target_end,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])
    for event in events:
        service.events().delete(calendarId="primary", eventId=event["id"]).execute()
        print(f"Deleted event: {event.get('summary', 'No Title')}")


def copy_events_to_date(service, events, target_date):
    """Copy events to a specified target date while keeping their time frames and colors."""
    for event in events:
        original_start = parser.isoparse(event["start"]["dateTime"])
        original_end = parser.isoparse(event["end"]["dateTime"])

        # Calculate the time delta (difference in days) between the original start date and the target date
        delta_days = (target_date - original_start.date()).days

        # Apply the delta to get the new start and end times
        new_start = original_start + datetime.timedelta(days=delta_days)
        new_end = original_end + datetime.timedelta(days=delta_days)

        event_copy = {
            "summary": event.get("summary"),
            "location": event.get("location"),
            "description": event.get("description"),
            "start": {"dateTime": new_start.isoformat()},
            "end": {"dateTime": new_end.isoformat()},
            "attendees": event.get("attendees"),
            "recurrence": event.get("recurrence"),
            "reminders": event.get("reminders"),
            "colorId": event.get("colorId"),  # Copy the event color
        }

        try:
            created_event = (
                service.events().insert(calendarId="primary", body=event_copy).execute()
            )
            print(f"Copied event: {created_event.get('summary')} to {target_date}")
        except HttpError as error:
            print(f"An error occurred while copying events: {error}")


def parse_date_input(date_input):
    """Parse user input to handle natural phrases and dates."""
    today = datetime.datetime.now().date()
    if date_input.lower() in ["today", "t", "now"]:
        return today
    elif date_input.lower() in ["tomorrow", "tmr"]:
        return today + datetime.timedelta(days=1)
    elif date_input.lower() in ["yesterday", "y"]:
        return today - datetime.timedelta(days=1)
    elif not date_input:
        # If the input is empty, default to today
        return today
    else:
        try:
            # Attempt to parse the date input
            return parser.parse(date_input).date()
        except ValueError:
            print("Invalid date format or phrase. Please try again.")
            return None


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

        # Get user input for the date to copy from
        copy_from_date_input = input(
            "Enter the date to copy events from (e.g., '2024-09-01', 'tomorrow', or 'yesterday'): "
        )

        # Parse the user input into a datetime object
        copy_from_date = parse_date_input(copy_from_date_input)
        if copy_from_date is None:
            return

        # Fetch events from the specified day
        events_to_copy = get_events_for_date(service, copy_from_date)
        if not events_to_copy:
            print("No events found on the specified date to copy.")
            return

        # Get user input for the target date (defaulting to today if blank)
        copy_to_date_input = input(
            "Enter the target date to copy events to (or press Enter to copy to today): "
        )
        copy_to_date = parse_date_input(copy_to_date_input)
        if copy_to_date is None:
            return

        # Delete events on the target date before copying
        delete_events_for_date(service, copy_to_date)

        # Copy events to the target date
        copy_events_to_date(service, events_to_copy, copy_to_date)

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
