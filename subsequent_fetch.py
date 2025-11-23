import os
from dotenv import load_dotenv
import boto3
import json
from botocore.exceptions import ClientError
import requests
import datetime

load_dotenv()

# OAuth2 application credentials
CLIENT_ID = os.getenv("OURA_CLIENT_ID")
CLIENT_SECRET = os.getenv("OURA_CLIENT_SECRET")

token_url = "https://api.ouraring.com/oauth/token"

# Establishes AWS session
region_name = "us-east-1"

session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name=region_name
)

# Create a Secrets Manager client
client = session.client(
    service_name='secretsmanager',
    region_name=region_name
)

# Pulls refresh token from secrets manager
secret_name = "oura-notification-refresh-token2"

get_secret_value_response = client.get_secret_value(
    SecretId=secret_name
)

secret = get_secret_value_response['SecretString']

secret = json.loads(secret)
access_token = secret["access-token"]
refresh_token = secret["oura-notification-refresh-token2"]
previous_stress_minutes = float(secret["stress-minutes"])

# Calls to daily stress endpoint
url = 'https://api.ouraring.com/v2/usercollection/daily_stress'
today = datetime.date.today().isoformat()
params={ 
    'start_date': f'{today}', 
    'end_date': f'{today}' 
}
headers = { 
  'Authorization': f'Bearer {access_token}' 
}
response = requests.request('GET', url, headers=headers, params=params).json()
recovery_seconds = response['data'][0]['recovery_high']
stress_seconds = response['data'][0]['stress_high']
stress_minutes = stress_seconds / 60

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

token = refresh_access_token(refresh_token)
access_token = token[0]
refresh_token = token[1]

# Updates secret manager
def update_secret(access_token, refresh_token, stress_minutes):
    client = session.client("secretsmanager")
    
    client.put_secret_value(
        SecretId="oura-notification-refresh-token2",
        SecretString=json.dumps({"access-token": access_token,
                                "oura-notification-refresh-token2": refresh_token,
                                 "stress-minutes": stress_minutes}) #access_token
    )

if (stress_minutes > previous_stress_minutes) or (stress_minutes == 0):
    update_secret(access_token, refresh_token, stress_minutes)
else:
    update_secret(access_token, refresh_token, previous_stress_minutes)

# Connection to AWS and SNS
session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name=region_name
)

sns = boto3.client("sns", region_name=region_name)
topic_arn = os.getenv("SNS_ARN")
print(topic_arn)
message = f"Your stress is likely high. Breathe deeply, get a massage, take a slow walk, nap, and hydrate. Message sent at {datetime.datetime.now()}"
subject = "Oura Stress Alert"

if stress_minutes > previous_stress_minutes:
    sns.publish(
        TopicArn=topic_arn,
        Message=message,
        Subject=subject
    )