# scripts/mark_unresponsive.py

import os
import boto3
from datetime import datetime, timezone
from dateutil import parser

# Load environment variables
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME")
SLACK_USER_IDS = os.getenv("SLACK_USER_IDS")  # Comma-separated user IDs

if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, DYNAMODB_TABLE_NAME, SLACK_USER_IDS]):
    raise Exception("❌ Missing required environment variables.")

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

# Scan attendance records
response = table.scan()
items = response.get("Items", [])

# Build lookup for latest attendance per user for today
latest_attendance = {}
username_lookup = {}

for item in items:
    uid = item.get("user_id")
    uname = item.get("username", "unknown")
    timestamp_str = item.get("timestamp")

    if not uid or not timestamp_str:
        continue

    try:
        timestamp = parser.parse(timestamp_str)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
    except Exception:
        continue

    username_lookup[uid] = uname

    if timestamp.date().isoformat() == today_str:
        existing_item = latest_attendance.get(uid)
        if not existing_item:
            latest_attendance[uid] = item
        else:
            existing_ts = parser.parse(existing_item["timestamp"])
            if existing_ts.tzinfo is None:
                existing_ts = existing_ts.replace(tzinfo=timezone.utc)
            if timestamp > existing_ts:
                latest_attendance[uid] = item

# Mark unresponsive users
for user_id in user_ids:
    if user_id not in latest_attendance:
        username = username_lookup.get(user_id, "unknown")
        table.put_item(Item={
            "user_id": user_id,
            "username": username,
            "status": "On Leave",
            "timestamp": f"{today_str}T00:00:00Z"
        })
        print(f"⚠️ Marked {user_id} ({username}) as On Leave (no response)")
    else:
        print(f"✅ {user_id} already responded: {latest_attendance[user_id]['status']}")
