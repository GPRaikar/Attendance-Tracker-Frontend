import os
import requests

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
# SLACK_USER_IDS = os.getenv("SLACK_USER_IDS")  # Comma-separated list of user IDs

SLACK_USER_IDS = [
    "U224TR5QU",    # Adarsh
    "U072YU9DJ4C",  # Nagraj
    "U05AM6K923B",  # Reejesh
    "U07AH9RCE4W",  # Samhitha
    "U07AGSC7GMU",  # Prathvi
    "U05KM0U9M7B",  # Raja
    "U07ASUK0M8C",  # Guruprasad
    "U05GQA7FG7N",  # Shubha
]

if not SLACK_BOT_TOKEN:
    raise Exception("Missing SLACK_BOT_TOKEN in environment variables.")

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
                "text": "📊 *View your attendance dashboard here:* <https://slack-attendance-tracker-backup.onrender.com|Attendance Dashboard>"
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
    if not SLACK_USER_IDS:
        print("⚠️ No user IDs configured in SLACK_USER_IDS.")
        return

    print(f"📨 Sending prompts to {len(SLACK_USER_IDS)} user(s)...")
    for uid in SLACK_USER_IDS:
        send_prompt(uid)


if __name__ == "__main__":
    main()
