import os
import boto3
from datetime import datetime, timezone
from dateutil import parser

# Load env variables
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME")
SLACK_USER_IDS = os.getenv("SLACK_USER_IDS")  # Comma-separated user IDs

if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, DYNAMODB_TABLE_NAME, SLACK_USER_IDS]):
    raise Exception("Missing required environment variables.")

# Set up DynamoDB
dynamodb = boto3.resource(
    "dynamodb",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)

# Get today's date in ISO format
today_str = datetime.now(timezone.utc).date().isoformat()

# Prepare user list
user_ids = [uid.strip() for uid in SLACK_USER_IDS.split(",") if uid.strip()]

# Fetch all attendance records
response = table.scan()
items = response.get("Items", [])

# Build lookup for latest (user_id, date)
latest_attendance = {}
for item in items:
    timestamp = item.get("timestamp")
    if not timestamp:
        continue
    date_str = parser.parse(timestamp).date().isoformat()
    if date_str == today_str:
        key = item["user_id"]
        if key not in latest_attendance or parser.parse(item["timestamp"]) > parser.parse(latest_attendance[key]["timestamp"]):
            latest_attendance[key] = item

# Mark unresponsive users
for user_id in user_ids:
    if user_id not in latest_attendance:
        # Add On Leave entry for unresponsive user
        username = "unknown"
        table.put_item(Item={
            "user_id": user_id,
            "username": username,
            "status": "On Leave",
            "timestamp": f"{today_str}T16:00:00Z"
        })
        print(f"⚠️ Marked {user_id} as On Leave (no response)")
    else:
        print(f"✅ {user_id} already responded: {latest_attendance[user_id]['status']}")
