"""
One-time Google Calendar OAuth setup.

Prerequisites (Google Cloud Console — https://console.cloud.google.com):
1. Create a project (or reuse one)
2. Enable the "Google Calendar API" (APIs & Services > Library)
3. Configure OAuth consent screen (External, add your Gmail as test user)
4. Create OAuth Client ID (type: Desktop app), download JSON
5. Save it as credentials.json in this folder
6. Run: python google_auth_setup.py  (browser opens, log in with rishikathakur607@gmail.com)

Produces token.json which calendar_service.py uses forever after (auto-refreshes).
"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]
HERE = os.path.dirname(os.path.abspath(__file__))
CREDS = os.path.join(HERE, "credentials.json")
TOKEN = os.path.join(HERE, "token.json")

if not os.path.exists(CREDS):
    raise SystemExit("credentials.json not found — download it from Google Cloud Console first (see docstring)")

# Fixed port: this redirect URI must be registered on the OAuth client in
# Google Cloud Console (web-type client): http://localhost:8765/
flow = InstalledAppFlow.from_client_secrets_file(CREDS, SCOPES)
creds = flow.run_local_server(port=8765)
with open(TOKEN, "w") as f:
    f.write(creds.to_json())
print(f"Success! token.json saved to {TOKEN}")
print("Aria can now check availability and create calendar events.")
