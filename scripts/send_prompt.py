import os
import requests

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_USER_IDS = os.getenv("SLACK_USER_IDS")  # Comma-separated list of user IDs


if not SLACK_BOT_TOKEN or not SLACK_USER_IDS:
    raise Exception("Missing SLACK_BOT_TOKEN or SLACK_USER_IDS in environment variables.")

headers = {
    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
    "Content-Type": "application/json"
}

block_message_template = {
    "text": "Please let us know your work status for today!",
    "blocks": [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "👋 Daily Attendance Check-in",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Where are you working today?*\nPlease select one of the following options:"
            }
        },
        {
            "type": "actions",
            "block_id": "attendance_main",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🏢 Work from Office"},
                    "value": "wfo",
                    "action_id": "wfo"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🏠 Work from Home"},
                    "value": "wfh",
                    "action_id": "wfh"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🌴 On Leave"},
                    "value": "leave",
                    "action_id": "leave"
                }
            ]
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "⏰ You have until *9 PM* to respond. If no response is received, you'll be marked as *On Leave* automatically."
                }
            ]
        },
        {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "📊 *View your attendance dashboard here:* <https://slack-attendance-tracker.onrender.com|Attendance Dashboard>"
        }
        }

    ]
}


def send_prompt(user_id):
    message = {
        "channel": user_id,
        **block_message_template
    }
    response = requests.post("https://slack.com/api/chat.postMessage", headers=headers, json=message)

    if response.ok and response.json().get("ok"):
        print(f"✅ Prompt sent to {user_id}")
    else:
        print(f"❌ Failed to send to {user_id}: {response.text}")


def main():
    user_ids = [uid.strip() for uid in SLACK_USER_IDS.split(",") if uid.strip()]
    if not user_ids:
        print("⚠️ No valid user IDs found in SLACK_USER_IDS.")
        return

    print(f"📨 Sending prompts to {len(user_ids)} user(s)...")
    for uid in user_ids:
        send_prompt(uid)


if __name__ == "__main__":
    main()
