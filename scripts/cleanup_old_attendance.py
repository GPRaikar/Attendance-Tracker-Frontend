"""Delete attendance records older than the retention window.

Set DRY_RUN=true to report what would be deleted without touching anything.
Only ever reads and writes the attendance table; holidays and change requests
live in their own tables and are never scanned.
"""

import json
import logging
import os
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "90"))
DRY_RUN = os.environ.get("DRY_RUN", "false").strip().lower() in ("1", "true", "yes")


def _scan_all():
    kwargs = {}
    table = common.attendance_table()
    while True:
        response = table.scan(**kwargs)
        yield from response.get("Items", [])
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return
        kwargs["ExclusiveStartKey"] = last_key


def delete_old_records():
    if common.ATTENDANCE_TABLE in (common.HOLIDAYS_TABLE, os.environ.get("CHANGE_REQUESTS_TABLE_NAME")):
        raise SystemExit("Refusing to run: DYNAMODB_TABLE_NAME points at a non-attendance table.")

    cutoff = common.today() - timedelta(days=RETENTION_DAYS)
    # ISO-8601 date prefixes compare correctly as plain strings.
    cutoff_key = f"{cutoff.isoformat()}T00:00:00"

    logger.info("Table %s in %s", common.ATTENDANCE_TABLE, common.AWS_REGION)
    logger.info("Deleting records before %s (%s days)", cutoff, RETENTION_DAYS)
    if DRY_RUN:
        logger.info("DRY_RUN is on; nothing will be deleted.")

    table = common.attendance_table()
    deleted = skipped = 0

    try:
        for item in _scan_all():
            user_id = item.get("user_id")
            timestamp = item.get("timestamp")
            if not user_id or not timestamp:
                skipped += 1
                continue
            if str(timestamp) >= cutoff_key:
                continue

            deleted += 1
            if DRY_RUN:
                logger.info("would delete %s / %s", user_id, timestamp)
                continue
            try:
                table.delete_item(Key={"user_id": user_id, "timestamp": timestamp})
            except Exception as error:  # noqa: BLE001 - one bad row must not stop the sweep
                deleted -= 1
                logger.error("could not delete %s/%s: %s", user_id, timestamp, error)
    except Exception as error:  # noqa: BLE001
        logger.error("Cleanup failed: %s", error)
        return {"statusCode": 500, "body": json.dumps({"message": "Cleanup failed", "error": str(error)})}

    logger.info("Done. %s record(s) %s, %s malformed row(s) skipped.",
                deleted, "would be deleted" if DRY_RUN else "deleted", skipped)
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Cleanup successful",
                "dry_run": DRY_RUN,
                "deleted_records": deleted,
                "skipped_records": skipped,
                "cutoff": cutoff.isoformat(),
            }
        ),
    }


if __name__ == "__main__":
    result = delete_old_records()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["statusCode"] == 200 else 1)
