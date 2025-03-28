import boto3
import csv
import json
import os
import requests

identitystore_client = boto3.client('identitystore')

IDENTITY_STORE_ID = 'd-xxxxxxxxxx'  # Replace with your value
GROUP_ID = 'g-xxxxxxxxxx'           # Replace with your value

SLACK_WEBHOOK_URL = os.environ['SLACK_WEBHOOK_URL']

def send_slack_notification(message):
    requests.post(SLACK_WEBHOOK_URL, json={"text": message})
    print(f"Slack response code: {response.status_code}")
    print(f"Slack response text: {response.text}")

def lambda_handler(event, context):
    try:
        body = event.get('body')
        if not body:
            raise Exception("No CSV body received from GitHub")

        reader = csv.DictReader(body.strip().splitlines())
        created = []

        for row in reader:
            print(f"Creating user: {row['Username']}")
            response = identitystore_client.create_user(
                IdentityStoreId=IDENTITY_STORE_ID,
                UserName=row['Username'],
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
            user_id = response['UserId']

            identitystore_client.create_group_membership(
                IdentityStoreId=IDENTITY_STORE_ID,
                GroupId=GROUP_ID,
                MemberId={'UserId': user_id}
            )
            created.append(row['Username'])

        send_slack_notification(f"✅ Created {len(created)} users: {', '.join(created)}")
        return {"statusCode": 200, "body": json.dumps({"message": "Users created"})}

    except Exception as e:
        send_slack_notification(f"❌ Error creating users: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

