import os.path
from datetime import datetime, timedelta

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Define task_duration as a static variable (in minutes)
task_duration = 15  # Set to 15 minutes

# SCOPES for Google Calendar API access
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Predefined Google Calendar colors (1-11) and their human-readable names
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

# Reverse the COLORS dictionary to map color names to their IDs
COLOR_NAME_TO_ID = {v: k for k, v in COLORS.items()}


def get_prayer_times(city="Istanbul", country="Turkey"):
    """Fetch prayer times from the Aladhan API for a specific location."""
    api_url = f"http://api.aladhan.com/v1/timingsByCity?city={city}&country={country}&method=2"

    try:
        response = requests.get(api_url)
        response.raise_for_status()

        data = response.json()
        prayer_times = data["data"]["timings"]

        turkish_prayers = {
            "Fajr": "Sabah",
            "Dhuhr": "Öğle",
            "Asr": "İkindi",
            "Maghrib": "Akşam",
            "Isha": "Yatsı",
        }

        print("Bugünün namaz vakitleri:")
        filtered_prayers = {}
        for prayer, turkish_name in turkish_prayers.items():
            print(f"{turkish_name} Namazı: {prayer_times[prayer]}")
            filtered_prayers[prayer] = {
                "name": turkish_name,
                "time": prayer_times[prayer],
            }

        return filtered_prayers

    except requests.exceptions.RequestException as e:
        print(f"Bir hata oluştu: {e}")
        return None


def add_event_to_calendar(service, prayer_name, start_time, end_time, color_id):
    """Add an event to Google Calendar with color."""
    event = {
        "summary": prayer_name,
        "start": {
            "dateTime": start_time,
            "timeZone": "Europe/Istanbul",  # Adjust as needed
        },
        "end": {
            "dateTime": end_time,
            "timeZone": "Europe/Istanbul",  # Adjust as needed
        },
        "colorId": color_id,  # Set the color for the event
    }

    try:
        event_result = (
            service.events().insert(calendarId="primary", body=event).execute()
        )
        print(
            f"Event created: {event_result['summary']} at {start_time} to {end_time} with color ID: {color_id}"
        )
    except HttpError as error:
        print(f"An error occurred: {error}")


def get_user_color_scheme():
    """Allow         user to define a color scheme using human-readable color names."""
    print("Available colors: " + ", ".join(COLORS.values()))
    color_scheme = {
        "Sabah": "Lavender",
        "Öğle": "Sage",
        "İkindi": "Grape",
        "Akşam": "Flamingo",
        "Yatsı": "Banana",
    }

    # Convert color names to their corresponding color IDs
    for prayer, color_name in color_scheme.items():
        if color_name not in COLOR_NAME_TO_ID:
            print(f"Invalid color name for {prayer}, using default 'Lavender'.")
            color_scheme[prayer] = "Lavender"  # Default to Lavender if invalid input

    # Replace color names with color IDs
    color_scheme_with_ids = {
        prayer: COLOR_NAME_TO_ID[color_name]
        for prayer, color_name in color_scheme.items()
    }

    return color_scheme_with_ids


def main():
    """Main function to fetch prayer times, create tasks around them, and apply colors."""
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
        # Build Google Calendar service
        service = build("calendar", "v3", credentials=creds)

        # Fetch prayer times
        prayer_times = get_prayer_times(city="Istanbul", country="Turkey")

        # Get the user's color scheme for each prayer
        color_scheme = get_user_color_scheme()

        # Calculate and add events to calendar with colors
        if prayer_times:
            for prayer_key, prayer_data in prayer_times.items():
                prayer_name = prayer_data["name"] + " Namazı"

                # Convert prayer time to datetime object
                prayer_time_str = prayer_data["time"]
                prayer_time = datetime.strptime(prayer_time_str, "%H:%M")

                # Calculate task start and end times
                task_start_time = prayer_time - timedelta(minutes=(task_duration // 3))
                task_end_time = prayer_time + timedelta(minutes=task_duration)

                # Format times for Google Calendar API
                today = datetime.now().date()
                task_start_time = datetime.combine(
                    today, task_start_time.time()
                ).isoformat()
                task_end_time = datetime.combine(
                    today, task_end_time.time()
                ).isoformat()

                # Fetch color ID for this prayer from the color scheme
                color_id = color_scheme[prayer_data["name"]]

                # Add event to Google Calendar with the chosen color
                add_event_to_calendar(
                    service, prayer_name, task_start_time, task_end_time, color_id
                )

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
