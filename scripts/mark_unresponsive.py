"""Mark anyone who never answered today's Slack prompt as On Leave.

Never overwrites an answer the person already gave, and does nothing at all on a
company holiday.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common

SLACK_USER_IDS = os.getenv("SLACK_USER_IDS")

if not SLACK_USER_IDS:
    raise SystemExit("❌ Missing SLACK_USER_IDS.")
if not os.getenv("DYNAMODB_TABLE_NAME"):
    raise SystemExit("❌ Missing DYNAMODB_TABLE_NAME.")


def main():
    day = common.today()

    holiday = common.get_holiday(day)
    if holiday:
        print(f"🎉 {day} is a company holiday ({holiday.get('name')}). Nobody is marked.")
        return 0

    user_ids = [uid.strip() for uid in SLACK_USER_IDS.split(",") if uid.strip()]
    marked = 0

    for user_id in user_ids:
        if common.has_record_for(user_id, day):
            print(f"✅ {user_id} already responded.")
            continue
        username = common.last_known_username(user_id)
        if common.create_if_absent(user_id, username, common.STATUS_LEAVE, day):
            marked += 1
            print(f"⚠️ Marked {user_id} ({username}) as On Leave (no response).")
        else:
            print(f"✅ {user_id} responded while this job was running; left untouched.")

    print(f"\nDone. {marked} of {len(user_ids)} user(s) marked On Leave for {day}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
