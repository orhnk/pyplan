import os
from datetime import datetime, timedelta

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuration constants
TASK_DURATION_MINUTES = 15  # Event duration in minutes
SCOPES = ["https://www.googleapis.com/auth/calendar"]
DEFAULT_TIMEZONE = "Europe/Istanbul"
API_BASE_URL = "http://api.aladhan.com/v1/timingsByCity"

# Predefined Google Calendar color names mapped to color IDs
COLORS = {
    "Lavender": "1",
    "Sage": "2",
    "Grape": "3",
    "Flamingo": "4",
    "Banana": "5",
    "Tangerine": "6",
    "Peacock": "7",
    "Graphite": "8",
    "Blueberry": "9",
    "Basil": "10",
    "Tomato": "11",
}

# Prayer color scheme mapped by prayer names
PRAYER_COLOR_SCHEME = {
    "Sabah": COLORS["Lavender"],
    "Öğle": COLORS["Sage"],
    "İkindi": COLORS["Grape"],
    "Akşam": COLORS["Flamingo"],
    "Yatsı": COLORS["Banana"],
}

# Map for English to Turkish prayer names
TURKISH_PRAYER_NAMES = {
    "Fajr": "Sabah",
    "Dhuhr": "Öğle",
    "Asr": "İkindi",
    "Maghrib": "Akşam",
    "Isha": "Yatsı",
}


def get_prayer_times(city="Istanbul", country="Turkey"):
    """Fetch prayer times from the Aladhan API for a specific location."""
    try:
        response = requests.get(
            f"{API_BASE_URL}?city={city}&country={country}&method=2"
        )
        response.raise_for_status()

        data = response.json()["data"]["timings"]
        return {
            prayer: {"name": TURKISH_PRAYER_NAMES[prayer], "time": time}
            for prayer, time in data.items()
            if prayer in TURKISH_PRAYER_NAMES
        }

    except requests.RequestException as e:
        print(f"Error fetching prayer times: {e}")
        return None


def add_event_to_calendar(service, prayer_name, start_time, end_time, color_id):
    """Add an event to Google Calendar."""
    event = {
        "summary": prayer_name,
        "start": {"dateTime": start_time, "timeZone": DEFAULT_TIMEZONE},
        "end": {"dateTime": end_time, "timeZone": DEFAULT_TIMEZONE},
        "colorId": color_id,
    }

    try:
        event_result = (
            service.events().insert(calendarId="primary", body=event).execute()
        )
        print(
            f"Created event: {event_result['summary']} from {start_time} to {end_time} with color ID: {color_id}"
        )
    except HttpError as error:
        print(f"Error adding event to calendar: {error}")


def authenticate_google_calendar():
    """Authenticate and return Google Calendar API service."""
    creds = None
    token_path = "secrets/cal-token.json"
    creds_path = "secrets/credentials.json"

    # Check if token file exists
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # If no valid credentials are available, login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def schedule_prayer_events(service, prayer_times):
    """Create and add prayer events to the calendar."""
    today = datetime.now().date()

    for prayer_key, prayer_data in prayer_times.items():
        prayer_name = f"{prayer_data['name']} Namazı"
        prayer_time = datetime.strptime(prayer_data["time"], "%H:%M").time()

        # Calculate start and end times for the event
        task_start = datetime.combine(today, prayer_time) - timedelta(
            minutes=TASK_DURATION_MINUTES // 3
        )
        task_end = task_start + timedelta(minutes=TASK_DURATION_MINUTES)

        # Format the times as required by the Google Calendar API
        task_start_iso = task_start.isoformat()
        task_end_iso = task_end.isoformat()

        # Fetch the color ID for the event
        color_id = PRAYER_COLOR_SCHEME.get(
            prayer_data["name"], COLORS["Lavender"]
        )  # Default to Lavender if not found

        # Add the event to Google Calendar
        add_event_to_calendar(
            service, prayer_name, task_start_iso, task_end_iso, color_id
        )


def main():
    """Main function to fetch prayer times, set up Google Calendar events."""
    try:
        service = authenticate_google_calendar()

        # Fetch today's prayer times
        prayer_times = get_prayer_times(city="Istanbul", country="Turkey")
        if not prayer_times:
            print("No prayer times available.")
            return

        # Schedule prayer events with colors
        schedule_prayer_events(service, prayer_times)

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
