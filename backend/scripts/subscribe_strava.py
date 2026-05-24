#!/usr/bin/env python3
"""
Create Strava webhook subscription so the app receives activity events.

Run from backend/:
  python -m scripts.subscribe_strava

Requires: STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_WEBHOOK_VERIFY_TOKEN, BACKEND_URL
"""
import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_root))

from src.core.config import (
    BACKEND_URL,
    STRAVA_CLIENT_ID,
    STRAVA_CLIENT_SECRET,
    STRAVA_WEBHOOK_CALLBACK_PATH,
    STRAVA_WEBHOOK_VERIFY_TOKEN,
)
from src.modules.third_party.strava.webhook_subscription import (
    create_subscription,
    delete_subscription,
    get_subscription,
)


def main() -> int:
    if not STRAVA_CLIENT_ID or not STRAVA_CLIENT_SECRET:
        print("Error: STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET must be set.")
        return 1
    if not STRAVA_WEBHOOK_VERIFY_TOKEN:
        print("Error: STRAVA_WEBHOOK_VERIFY_TOKEN must be set.")
        return 1
    if not BACKEND_URL:
        print("Error: BACKEND_URL must be set (e.g. https://your-api.example.com or ngrok URL).")
        return 1

    callback_url = f"{BACKEND_URL.rstrip('/')}{STRAVA_WEBHOOK_CALLBACK_PATH}"
    print(f"Callback URL: {callback_url}")
    print()

    try:
        existing = get_subscription(STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET)
    except Exception as e:
        print(f"Failed to get existing subscription: {e}")
        return 1

    if existing:
        subs = existing if isinstance(existing, list) else [existing]
        print(f"Existing subscription(s): {subs}")
        sub_id = subs[0].get("id") if isinstance(subs[0], dict) else subs[0]
        if sub_id is not None:
            try:
                delete_subscription(int(sub_id), STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET)
                print(f"Deleted existing subscription id={sub_id}")
            except Exception as e:
                print(f"Failed to delete existing subscription: {e}")
                return 1
        print()

    try:
        result = create_subscription(
            client_id=STRAVA_CLIENT_ID,
            client_secret=STRAVA_CLIENT_SECRET,
            callback_url=callback_url,
            verify_token=STRAVA_WEBHOOK_VERIFY_TOKEN,
        )
        print(f"Subscription created: {result}")
        return 0
    except Exception as e:
        print(f"Failed to create subscription: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
