"""
Strava webhook subscription management: create, get, delete push subscription.
One subscription per Strava app; callback receives events for all authorized athletes.
"""
import requests

STRAVA_PUSH_SUBSCRIPTIONS_URL = "https://www.strava.com/api/v3/push_subscriptions"


def create_subscription(
    client_id: str,
    client_secret: str,
    callback_url: str,
    verify_token: str,
) -> dict:
    """
    Create a webhook subscription with Strava.
    Strava will send a GET to callback_url to validate; your endpoint must respond
    with 200 and {"hub.challenge": "<challenge>"} for subscription to be created.

    Returns: {"id": <subscription_id>} on success.
    Raises: requests.RequestException on HTTP errors.
    """
    resp = requests.post(
        STRAVA_PUSH_SUBSCRIPTIONS_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "callback_url": callback_url,
            "verify_token": verify_token,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def get_subscription(client_id: str, client_secret: str) -> list[dict]:
    """
    Get existing webhook subscription(s) for the app.
    Returns list of subscription objects (usually 0 or 1).
    """
    resp = requests.get(
        STRAVA_PUSH_SUBSCRIPTIONS_URL,
        params={
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def delete_subscription(
    subscription_id: int,
    client_id: str,
    client_secret: str,
) -> None:
    """Delete a webhook subscription by ID. Returns 204 on success."""
    resp = requests.delete(
        f"{STRAVA_PUSH_SUBSCRIPTIONS_URL}/{subscription_id}",
        params={
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=10,
    )
    resp.raise_for_status()
