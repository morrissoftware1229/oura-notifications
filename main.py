import os
from dotenv import load_dotenv
import requests
import json
from urllib.parse import urlencode
import webbrowser
from flask import Flask, request
import time
import threading

load_dotenv()

# Your OAuth2 application credentials
CLIENT_ID = os.getenv("OURA_CLIENT_ID")
CLIENT_SECRET = os.getenv("OURA_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:5000/callback"

# Flask server code, so we can automatically capture our code
app = Flask(__name__)
auth_code = None

@app.route("/callback")
def callback():
    global auth_code
    auth_code = request.args.get("code")
    return auth_code

def run_server():
    app.run(port=5000)

# Starting the server in a background thread
threading.Thread(target=run_server, daemon=True).start()
time.sleep(3)  # brief pause to ensure server starts

# Step 1: Direct user to authorization page
auth_params = {
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": "daily heartrate personal"
}
auth_url = f"https://cloud.ouraring.com/oauth/authorize?{urlencode(auth_params)}"
webbrowser.open(auth_url)

# Gives Flask time to open browswer and retrieve code
time.sleep(15)

# Step 2: Exchange authorization code for access token
# After user authorizes, they'll be redirected to your redirect URI with a code parameter
token_url = "https://api.ouraring.com/oauth/token"
token_data = {
    "grant_type": "authorization_code",
    "code": auth_code,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "redirect_uri": REDIRECT_URI
}
response = requests.post(token_url, data=token_data)
tokens = response.json()
print(tokens)
access_token = tokens["access_token"]
refresh_token = tokens["refresh_token"]

# Step 3: Use the access token to make API calls
headers = {"Authorization": f"Bearer {access_token}"}
sleep_data = requests.get(
    "https://api.ouraring.com/v2/usercollection/sleep",
    headers=headers,
    params={"start_date": "2025-08-01", "end_date": "2025-08-31"}
)
print(json.dumps(sleep_data.json(), indent=2))

# Step 4: Refresh the token when it expires
def refresh_access_token(refresh_token):
    token_data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    response = requests.post(token_url, data=token_data)
    new_tokens = response.json()
    return new_tokens["access_token"], new_tokens["refresh_token"]