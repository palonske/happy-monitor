import os
import json
import requests
from collections import defaultdict

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
PARK_NAMES = {"DLR_DP": "Disneyland Park", "DLR_CA": "Disney California Adventure"}


def fetch_availability(date):
    url = (
        "https://disneyland.disney.go.com/availability-calendar/api/calendar"
        f"?segment=offer&startDate={date}&endDate={date}"
    )
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    for entry in resp.json():
        if entry["date"] == date:
            return {f["facilityName"]: f["available"] for f in entry["facilities"]}
    return {}


def is_available(availability, park_pref):
    if park_pref == "either":
        return any(availability.values())
    return availability.get(park_pref, False)


def send_alert(webhook_url, name, date, availability):
    open_parks = [PARK_NAMES.get(k, k) for k, v in availability.items() if v]
    parks_str = " and ".join(open_parks)
    requests.post(
        webhook_url,
        json={
            "content": (
                f"🎢 **Hey {name} — Disneyland availability opened!**\n"
                f"{parks_str} has reservations for **{date}**.\n"
                f"Book now → <https://disneyland.disney.go.com/reservations/>"
            )
        },
        timeout=10,
    )


with open("subscriptions.json") as f:
    subscriptions = json.load(f)

by_date = defaultdict(list)
for sub in subscriptions:
    by_date[sub["date"]].append(sub)

for date, subs in by_date.items():
    availability = fetch_availability(date)
    print(f"{date}: {availability}")
    for sub in subs:
        if is_available(availability, sub["park"]):
            webhook_url = os.environ.get(sub["webhook_env"])
            if not webhook_url:
                print(f"  WARNING: no secret found for {sub['webhook_env']}")
                continue
            send_alert(webhook_url, sub["name"], date, availability)
            print(f"  Alerted {sub['name']}")
        else:
            print(f"  Not available for {sub['name']}")
