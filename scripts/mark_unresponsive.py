#Built a username_lookup dictionary using past entries, Fallback to "unknown" only if username was never recorded.

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
    raise Exception("Missing required environment variables.")

# Set up DynamoDB
dynamodb = boto3.resource(
    "dynamodb",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)

# Today's date in ISO format
today_str = datetime.now(timezone.utc).date().isoformat()

# Prepare user list
user_ids = [uid.strip() for uid in SLACK_USER_IDS.split(",") if uid.strip()]

# Scan attendance records
response = table.scan()
items = response.get("Items", [])

# Build lookup of latest attendance per user for today
latest_attendance = {}
username_lookup = {}

for item in items:
    uid = item.get("user_id")
    uname = item.get("username", "unknown")
    timestamp = item.get("timestamp")

    if uid and uname:
        username_lookup[uid] = uname  # store latest seen username

    if not timestamp:
        continue

    date_str = parser.parse(timestamp).date().isoformat()
    if date_str == today_str:
        if uid not in latest_attendance or parser.parse(timestamp) > parser.parse(latest_attendance[uid]["timestamp"]):
            latest_attendance[uid] = item

# Mark unresponsive users
for user_id in user_ids:
    if user_id not in latest_attendance:
        username = username_lookup.get(user_id, "unknown")
        table.put_item(Item={
            "user_id": user_id,
            "username": username,
            "status": "On Leave",
            "timestamp": f"{today_str}T19:00:00Z"
        })
        print(f"⚠️ Marked {user_id} ({username}) as On Leave (no response)")
    else:
        print(f"✅ {user_id} already responded: {latest_attendance[user_id]['status']}")

# ------------------------------------------------------------------------------------------------------------------------------------
# Optimized mark_unresponsive.py

# import os
# import boto3
# from datetime import datetime, timezone
# from dateutil import parser

# # Load environment variables
# AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
# AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
# AWS_REGION = os.getenv("AWS_REGION")
# DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME")
# SLACK_USER_IDS = os.getenv("SLACK_USER_IDS")  # Comma-separated user IDs

# # Validation
# if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, DYNAMODB_TABLE_NAME, SLACK_USER_IDS]):
#     raise Exception("❌ Missing required environment variables.")

# # Set up DynamoDB
# dynamodb = boto3.resource(
#     "dynamodb",
#     aws_access_key_id=AWS_ACCESS_KEY_ID,
#     aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#     region_name=AWS_REGION
# )
# table = dynamodb.Table(DYNAMODB_TABLE_NAME)

# # Get today's date in ISO format
# today_str = datetime.now(timezone.utc).date().isoformat()

# # Prepare user list
# user_ids = [uid.strip() for uid in SLACK_USER_IDS.split(",") if uid.strip()]

# # Fetch all records
# response = table.scan()
# items = response.get("Items", [])

# # Find latest status per user for today
# latest_attendance = {}
# username_lookup = {}

# for item in items:
#     if not item.get("timestamp") or not item.get("user_id"):
#         continue

#     date_str = parser.parse(item["timestamp"]).date().isoformat()
#     if date_str != today_str:
#         continue

#     user_id = item["user_id"]
#     timestamp = parser.parse(item["timestamp"])

#     if user_id not in latest_attendance or timestamp > parser.parse(latest_attendance[user_id]["timestamp"]):
#         latest_attendance[user_id] = item
#         username_lookup[user_id] = item.get("username", "unknown")

# # Add On Leave entries for users who didn't respond
# for user_id in user_ids:
#     if user_id not in latest_attendance:
#         username = username_lookup.get(user_id, "unknown")
#         item = {
#             "user_id": user_id,
#             "username": username,
#             "status": "On Leave",
#             "timestamp": f"{today_str}T16:00:00Z"
#         }
#         table.put_item(Item=item)
#         print(f"⚠️ Marked {user_id} ({username}) as On Leave (no response)")
#     else:
#         status = latest_attendance[user_id]["status"]
#         print(f"✅ {user_id} already responded: {status}")
