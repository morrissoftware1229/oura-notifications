import os
from dotenv import load_dotenv
import requests
import json
from urllib.parse import urlencode
import webbrowser
from flask import Flask, request
import time
import threading
from datetime import date
import boto3

load_dotenv()

# OAuth2 application credentials
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

# Starts the server in a background thread
threading.Thread(target=run_server, daemon=True).start()
time.sleep(3)  # brief pause to ensure server starts

# Directs user to authorization page
auth_params = {
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": "daily stress personal"
}
auth_url = f"https://cloud.ouraring.com/oauth/authorize?{urlencode(auth_params)}"
webbrowser.open(auth_url)

# Gives Flask time to open browswer and retrieve code
time.sleep(8)

# Exchanges authorization code for access token
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

# Uses the access token to get stress information
url = 'https://api.ouraring.com/v2/usercollection/daily_stress'
today = date.today().isoformat()
params={ 
    'start_date': f'{today}', 
    'end_date': f'{today}' 
}
headers = { 
  'Authorization': f'Bearer {access_token}' 
}
response = requests.request('GET', url, headers=headers, params=params).json()
recovery_seconds = response['data'][0]['recovery_high']
stress_seconds = response['data'][0]['recovery_high']
print(f"recovery minutes are {recovery_seconds/60}")
print(f"stress minutes are {stress_seconds/60}")

# Refreshes the token when it expires
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

# Connection to AWS and SNS
session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name="us-east-1"
)

sns = boto3.client("sns", region_name="us-east-1")
topic_arn = os.getenv("SNS_ARN")
print(topic_arn)
message = "High stress detected! Take a recovery walk and hydrate."
subject = "Oura Stress Alert"

if stress_seconds > 0:
    sns.publish(
        TopicArn=topic_arn,
        Message=message,
        Subject=subject
    )

