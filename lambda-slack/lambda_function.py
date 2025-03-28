# lambda_function.py
import boto3
import csv
import os
import json
import urllib.parse
import requests

s3 = boto3.client('s3')
identitystore = boto3.client('identitystore')

IDENTITY_STORE_ID = 'd-9067d1167c'                          # Replace with your actual ID
GROUP_ID = '645864e8-2041-7088-69b0-7517e985e781'           # Replace with your actual group ID
SLACK_WEBHOOK_URL = os.environ['SLACK_WEBHOOK_URL']

def send_slack_notification(message):
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json={"text": message})
        print(f"Slack response: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Slack notification failed: {e}")

def user_exists(username):
    try:
        response = identitystore.list_users(
            IdentityStoreId=IDENTITY_STORE_ID,
            Filters=[
                {
                    'AttributePath': 'UserName',
                    'AttributeValue': username
                }
            ]
        )
        return len(response['Users']) > 0
    except Exception as e:
        print(f"Error checking user existence: {e}")
        return False

def lambda_handler(event, context):
    print("Event received:", json.dumps(event))
    
    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])

        response = s3.get_object(Bucket=bucket, Key=key)
        csv_content = response['Body'].read().decode('utf-8').splitlines()
        reader = csv.DictReader(csv_content)

        created_users = []
        skipped_users = []

        for row in reader:
            username = row['Username']
            if user_exists(username):
                print(f"User {username} already exists. Skipping.")
                skipped_users.append(username)
                continue

            user_response = identitystore.create_user(
                IdentityStoreId=IDENTITY_STORE_ID,
                UserName=username,
                DisplayName=f"{row['FirstName']} {row['LastName']}",
                Name={
                    'GivenName': row['FirstName'],
                    'FamilyName': row['LastName']
                },
                Emails=[{
                    'Value': row['Email'],
                    'Type': 'work',
                    'Primary': True
                }]
            )
            user_id = user_response['UserId']

            identitystore.create_group_membership(
                IdentityStoreId=IDENTITY_STORE_ID,
                GroupId=GROUP_ID,
                MemberId={'UserId': user_id}
            )

            created_users.append(username)

        message = f"✅ Lambda User Sync Completed\nCreated: {created_users}\nSkipped: {skipped_users}"
        print(message)
        send_slack_notification(message)
        return {"statusCode": 200, "body": message}

    except Exception as e:
        error_msg = f"❌ Lambda error: {str(e)}"
        print(error_msg)
        send_slack_notification(error_msg)
        return {"statusCode": 500, "body": error_msg}
