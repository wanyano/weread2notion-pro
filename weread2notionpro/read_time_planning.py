"""Pure helpers for safe, per-calendar-year WeRead reading-time reconciliation.

WeRead /readdata/detail monthly readTimes are per-day seconds keyed by Unix
timestamps, not minutes. The existing Pro 日 database also stores seconds.
No Notion writes are performed in this module.
"""
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))


def local_midnight_timestamp(day):
    """Unix seconds for 00:00 Asia/Shanghai of YYYY-MM-DD."""
    return int(datetime.fromisoformat(day).replace(tzinfo=TZ).timestamp())


def monthly_daily_seconds(payload, year, month):
    """Validate the monthly Gateway response and extract day -> integer seconds.

    Fail closed on malformed/ambiguous statistics. A truly empty month is OK.
    """
    if not isinstance(payload, dict):
        raise ValueError("WeRead monthly statistics must be a JSON object")
    times = payload.get("readTimes")
    total = payload.get("totalReadTime", 0)
    if times is None and total in (None, 0):
        return {}
    if not isinstance(times, dict):
        raise ValueError("WeRead monthly response lacks daily readTimes object")
    if not isinstance(total, (int, float)) or isinstance(total, bool) or total < 0:
        raise ValueError("Invalid monthly totalReadTime")

    by_day = {}
    for key, duration in times.items():
        try:
            stamp = int(key)
            dt = datetime.fromtimestamp(stamp, TZ)
        except (ValueError, TypeError, OverflowError, OSError) as exc:
            raise ValueError("Invalid daily timestamp from WeRead") from exc
        if dt.year != year or dt.month != month:
            raise ValueError("WeRead monthly data contains an out-of-period daily bucket")
        if not isinstance(duration, (int, float)) or isinstance(duration, bool):
            raise ValueError("Invalid daily reading duration type")
        if duration < 0 or int(duration) != duration:
            raise ValueError("Daily duration must be a nonnegative number of seconds")
        day = dt.date().isoformat()
        if day in by_day:
            raise ValueError("Duplicate daily bucket for the same local date")
        by_day[day] = int(duration)

    if total > 0 and not by_day:
        raise ValueError("Nonzero monthly reading total but no usable daily buckets")
    return by_day


def daily_reconciliation(source_days, existing_rows, year):
    """Plan creates/updates without deleting or resetting any existing entries.

    Existing rows: {id, timestamp, duration}; duplicate dates fail closed.
    Source zero-duration days are ignored so a missing bucket cannot erase
    previously recorded reading time.
    """
    if not isinstance(source_days, dict):
        raise ValueError("Expected a day-to-seconds mapping")
    by_day = {}
    for item in existing_rows:
        stamp = item.get("timestamp")
        if stamp is None:
            continue
        try:
            day_dt = datetime.fromtimestamp(int(stamp), TZ)
        except (ValueError, TypeError, OverflowError, OSError) as exc:
            raise ValueError("Invalid existing Notion daily timestamp") from exc
        if day_dt.year != year:
            continue
        day = day_dt.date().isoformat()
        if day in by_day:
            raise ValueError("Duplicate Notion day records; resolve before importing")
        by_day[day] = item

    creates, updates, unchanged = [], [], 0
    for day, seconds in sorted(source_days.items()):
        parsed = datetime.fromisoformat(day)
        if parsed.year != year:
            raise ValueError("Source day outside selected year")
        if not isinstance(seconds, int) or isinstance(seconds, bool) or seconds < 0:
            raise ValueError("Invalid source daily duration")
        if seconds == 0:
            # Never create empty days or zero out historical records.
            continue
        current = by_day.get(day)
        timestamp = local_midnight_timestamp(day)
        if current is None:
            creates.append({"day": day, "timestamp": timestamp, "seconds": seconds})
        elif current.get("duration") != seconds:
            updates.append({
                "day": day, "timestamp": timestamp, "seconds": seconds,
                "page_id": current["id"],
            })
        else:
            unchanged += 1
    return {"create": creates, "update": updates, "unchanged": unchanged}
