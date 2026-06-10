# Strava Webhook Subscription

The app receives Strava activity events (create/update/delete) via a webhook. One subscription per Strava app covers all connected users.

## Create the subscription

Run the management script once per environment (or when the callback URL changes):

```bash
# From project root
python scripts/subscribe_strava.py
# or
python -m scripts.subscribe_strava
```

**Requirements:**

- Environment variables set (e.g. in `.env`): `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, `STRAVA_WEBHOOK_VERIFY_TOKEN`, `BACKEND_URL`
- Optional: `STRAVA_WEBHOOK_CALLBACK_PATH` (default `/api/webhooks/strava`)
- The backend must be **reachable** at `BACKEND_URL` when you run the script; Strava sends a GET request to the callback URL to validate it. For local development use a tunnel (e.g. ngrok).

**Behaviour:**

- Callback URL used: `{BACKEND_URL}{STRAVA_WEBHOOK_CALLBACK_PATH}` (e.g. `https://your-api.example.com/api/webhooks/strava`)
- If a subscription already exists, it is deleted and a new one is created (re-running the script refreshes the subscription)
- On success, the script prints the new subscription id

## Verification endpoint

The FastAPI backend must respond to Strava’s validation GET with status 200 and body `{"hub.challenge": "<challenge>"}`. This is implemented at `GET /api/webhooks/strava`; ensure `STRAVA_WEBHOOK_VERIFY_TOKEN` matches the token you pass when creating the subscription.

## Event handling

- **Activity create:** When an activity is created in Strava, the webhook handler fetches it, checks if it’s a running type (Run, VirtualRun, Treadmill, etc.), and if so creates an Activity in the DB with the user’s default shoe and updates the shoe’s `distance_covered_km`.
- **Activity update:** When an activity's title is changed in Strava, the webhook handler updates the corresponding Activity's `name` in the database.
- Respond with 200 within 2 seconds; processing runs in a background thread.

## Troubleshooting

- **Subscription creation fails:** Ensure the callback URL is publicly reachable and returns 200 with the challenge. If your app doesn’t have webhook access yet, contact developers@strava.com.
- **No events received:** Confirm the subscription was created (run the script and note the id). Check that athletes have authorized the app and that the backend is reachable at `BACKEND_URL`.
