"""Pure helpers for safe, monotonic WeRead reading-time reconciliation."""
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))


def local_midnight_timestamp(day):
    """Unix seconds for 00:00 Asia/Shanghai of YYYY-MM-DD."""
    return int(datetime.fromisoformat(day).replace(tzinfo=TZ).timestamp())


def monthly_daily_seconds(payload, year, month):
    """Validate one monthly Gateway response and return day -> seconds."""
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
    """Plan monotonic creates/updates without deleting or reducing history."""
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
        duration = item.get("duration")
        if duration is not None and (
            not isinstance(duration, (int, float))
            or isinstance(duration, bool)
            or duration < 0
            or int(duration) != duration
        ):
            raise ValueError("Invalid existing Notion daily duration")
        by_day[day] = item

    creates, updates = [], []
    unchanged = preserved = 0
    for day, seconds in sorted(source_days.items()):
        parsed = datetime.fromisoformat(day)
        if parsed.year != year:
            raise ValueError("Source day outside selected year")
        if not isinstance(seconds, int) or isinstance(seconds, bool) or seconds < 0:
            raise ValueError("Invalid source daily duration")
        if seconds == 0:
            continue
        current = by_day.get(day)
        timestamp = local_midnight_timestamp(day)
        if current is None:
            creates.append({"day": day, "timestamp": timestamp, "seconds": seconds})
            continue
        current_seconds = current.get("duration")
        if current_seconds is None or seconds > current_seconds:
            updates.append({
                "day": day,
                "timestamp": timestamp,
                "seconds": seconds,
                "page_id": current["id"],
            })
        elif seconds == current_seconds:
            unchanged += 1
        else:
            preserved += 1
    return {
        "create": creates,
        "update": updates,
        "unchanged": unchanged,
        "preserved": preserved,
    }

