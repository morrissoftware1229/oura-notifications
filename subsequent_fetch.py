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
session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
    region_name="us-east-1"
)

# Pulls refresh token from secrets manager
def get_secret():

    secret_name = "oura-notification-refresh-token2"
    region_name = "us-east-1"

    # Create a Secrets Manager client
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    secret = get_secret_value_response['SecretString']
    return secret

secret = get_secret()
secret = json.loads(secret)
print(secret)
refresh_token = secret["oura-notification-refresh-token"]
print(refresh_token)

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
print(token)
# access_token = token[0]
# refresh_token = token[1]

# # Updates secret manager
# def update_secret(refresh_token):
#     client = session.client("secretsmanager")
    
#     client.put_secret_value(
#         SecretId="oura-notification-refresh-token2",
#         SecretString=json.dumps({"oura-notification-refresh-token": access_token}) #access_token
#     )
#     return print("Secret Updated")

# update_secret(refresh_token)

# # Calls to daily stress endpoint
# url = 'https://api.ouraring.com/v2/usercollection/daily_stress'
# today = datetime.date.today().isoformat()
# params={ 
#     'start_date': f'{today}', 
#     'end_date': f'{today}' 
# }
# headers = { 
#   'Authorization': f'Bearer {access_token}' 
# }
# response = requests.request('GET', url, headers=headers, params=params).json()
# print(response)
# recovery_seconds = response['data'][0]['recovery_high']
# stress_seconds = response['data'][0]['recovery_high']
# print(f"recovery minutes are {recovery_seconds/60}")
# print(f"stress minutes are {stress_seconds/60}")

# # Connection to AWS and SNS
# session = boto3.Session(
#     aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
#     aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
#     region_name="us-east-1"
# )

# sns = boto3.client("sns", region_name="us-east-1")
# topic_arn = os.getenv("SNS_ARN")
# print(topic_arn)
# message = f"Your stress is likely high. Breathe deeply, get a massage, take a slow walk, nap, and hydrate. Message sent at {datetime.datetime.now()}"
# subject = "Oura Stress Alert"

# if recovery_seconds == True:
#     sns.publish(
#         TopicArn=topic_arn,
#         Message=message,
#         Subject=subject
#     )