"""Send the daily Slack attendance check-in.

Skips company holidays entirely, and sends the five-button message (Office, Home,
Leave, Log In, Log Out) that the backend re-renders in place on every click.
"""

import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_USER_IDS = os.getenv("SLACK_USER_IDS")
DASHBOARD_URL = os.getenv(
    "APP_BASE_URL", "https://slack-attendance-tracker-backup.onrender.com"
).rstrip("/")

if not SLACK_BOT_TOKEN or not SLACK_USER_IDS:
    raise SystemExit("Missing SLACK_BOT_TOKEN or SLACK_USER_IDS in environment variables.")

headers = {
    "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
    "Content-Type": "application/json",
}


def build_message(day):
    return {
        "text": "Please let us know your work status for today!",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "👋 Daily Attendance Check-in",
                    "emoji": True,
                },
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": day.strftime("%A, %d %B %Y")}],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "_Not recorded yet_\n*Login* `—`   ·   *Logout* `—`",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Where are you working today?*"},
            },
            {
                "type": "actions",
                "block_id": "attendance_status",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🏢 Work from Office", "emoji": True},
                        "value": "wfo",
                        "action_id": "wfo",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🏠 Work from Home", "emoji": True},
                        "value": "wfh",
                        "action_id": "wfh",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🌴 On Leave", "emoji": True},
                        "value": "leave",
                        "action_id": "leave",
                    },
                ],
            },
            {
                "type": "actions",
                "block_id": "attendance_times",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🕘 Log In", "emoji": True},
                        "value": "login",
                        "action_id": "login",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🌙 Log Out", "emoji": True},
                        "value": "logout",
                        "action_id": "logout",
                    },
                ],
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            "⏰ Respond by *9 PM* or you'll be marked *On Leave* automatically. "
                            "Tap *Log Out* when you finish for the day."
                        ),
                    }
                ],
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"📊 <{DASHBOARD_URL}/calendar|Attendance dashboard> · "
                        f"<{DASHBOARD_URL}/request-change|Request a correction>",
                    }
                ],
            },
        ],
    }


def send_prompt(user_id, message):
    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers=headers,
        json={"channel": user_id, **message},
        timeout=15,
    )
    if response.ok and response.json().get("ok"):
        print(f"✅ Prompt sent to {user_id}")
        return True
    print(f"❌ Failed to send to {user_id}: {response.text}")
    return False


def main():
    day = common.today()

    holiday = common.get_holiday(day)
    if holiday:
        print(f"🎉 {day} is a company holiday ({holiday.get('name')}). No prompts sent.")
        return 0

    user_ids = [uid.strip() for uid in SLACK_USER_IDS.split(",") if uid.strip()]
    if not user_ids:
        print("⚠️ No valid user IDs found in SLACK_USER_IDS.")
        return 0

    message = build_message(day)
    print(f"📨 Sending prompts to {len(user_ids)} user(s) for {day}...")
    failures = sum(0 if send_prompt(uid, message) else 1 for uid in user_ids)

    if failures:
        print(f"❌ {failures} prompt(s) failed to send.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
