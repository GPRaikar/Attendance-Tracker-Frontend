"""Shared helpers for the scheduled attendance jobs.

Mirrors the canonical record shape used by the web app: one item per person per
local day, sort key = local midnight.
"""

from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
TZ = ZoneInfo(APP_TIMEZONE)

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
ATTENDANCE_TABLE = os.getenv("DYNAMODB_TABLE_NAME", "SlackAttendance")
HOLIDAYS_TABLE = os.getenv("HOLIDAYS_TABLE_NAME", "CompanyHolidays")
DYNAMODB_ENDPOINT_URL = os.getenv("DYNAMODB_ENDPOINT_URL", "")

STATUS_WFO = "Work from Office"
STATUS_WFH = "Work from Home"
STATUS_LEAVE = "On Leave"

_resource = None


def resource():
    global _resource
    if _resource is None:
        kwargs = {"region_name": AWS_REGION}
        if DYNAMODB_ENDPOINT_URL:
            kwargs["endpoint_url"] = DYNAMODB_ENDPOINT_URL
        _resource = boto3.resource("dynamodb", **kwargs)
    return _resource


def attendance_table():
    return resource().Table(ATTENDANCE_TABLE)


def holidays_table():
    return resource().Table(HOLIDAYS_TABLE)


def today() -> date:
    return datetime.now(TZ).date()


def day_key(day: date) -> str:
    return datetime.combine(day, time.min, tzinfo=TZ).isoformat()


def day_bounds(start: date, end: date) -> tuple[str, str]:
    return f"{start.isoformat()}T00:00:00", f"{(end + timedelta(days=1)).isoformat()}T00:00:00"


def get_holiday(day: date) -> dict | None:
    """Returns the holiday item for a day, or None. Never raises on a missing table."""
    try:
        return holidays_table().get_item(Key={"holiday_date": day.isoformat()}).get("Item")
    except ClientError as error:
        if error.response["Error"]["Code"] == "ResourceNotFoundException":
            print(
                f"! {HOLIDAYS_TABLE} does not exist; treating {day} as a working day. "
                "Run scripts/bootstrap_tables.py in the backend repo to create it."
            )
            return None
        raise


def has_record_for(user_id: str, day: date) -> bool:
    """True when the person already has any record for that local day, legacy rows included."""
    low, high = day_bounds(day, day)
    response = attendance_table().query(
        KeyConditionExpression=Key("user_id").eq(user_id) & Key("timestamp").between(low, high),
        ProjectionExpression="user_id",
        Limit=1,
    )
    return bool(response.get("Items"))


def last_known_username(user_id: str, default: str = "unknown") -> str:
    response = attendance_table().query(
        KeyConditionExpression=Key("user_id").eq(user_id),
        ScanIndexForward=False,
        Limit=1,
    )
    items = response.get("Items", [])
    return items[0].get("username", default) if items else default


def create_if_absent(user_id: str, username: str, status: str, day: date) -> bool:
    """Write a canonical record only when that exact day-key item is missing."""
    try:
        attendance_table().put_item(
            Item={
                "user_id": user_id,
                "timestamp": day_key(day),
                "date": day.isoformat(),
                "username": username,
                "status": status,
                "source": "auto",
                "updated_at": datetime.now(TZ).isoformat(),
            },
            ConditionExpression=Attr("user_id").not_exists(),
        )
        return True
    except ClientError as error:
        if error.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise
