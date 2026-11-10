"""Safely restore daily reading-time sync in the existing Notion Pro layout.

Default is a read-only preview. Import requires an explicit workflow selection.
Heatmap generation is intentionally separate and is not a prerequisite.
"""
import os
from datetime import datetime

from weread2notionpro.read_time_planning import (
    TZ,
    daily_reconciliation,
    local_midnight_timestamp,
    monthly_daily_seconds,
)
from weread2notionpro.utils import (
    get_date,
    get_icon,
    get_number,
    get_relation,
    get_title,
)


def month_start_unix(year, month):
    return local_midnight_timestamp(f"{year:04d}-{month:02d}-01")


def fetch_year_daily(api, year):
    """Read each month from the Gateway before planning any Notion change."""
    today = datetime.now(TZ)
    if year > today.year:
        raise ValueError("Future calendar year cannot be synchronized")
    days = {}
    months = range(1, 13) if year < today.year else range(1, today.month + 1)
    for month in months:
        data = api.get_read_statistics(
            mode="monthly", base_time=month_start_unix(year, month)
        )
        part = monthly_daily_seconds(data, year, month)
        overlap = days.keys() & part.keys()
        if overlap:
            raise ValueError("Duplicate day across monthly statistics")
        days.update(part)
        print(f"READ_TIME_MONTH: {year:04d}-{month:02d} days={len(part)}")
    return days


def read_existing_days(helper):
    if not helper.day_database_id:
        raise ValueError("Missing the Pro 日 database")
    results = helper.query_all(helper.day_database_id)
    rows = []
    for result in results:
        fields = result.get("properties") or {}
        timestamp_prop = fields.get("时间戳") or {}
        duration_prop = fields.get("时长") or {}
        stamp = timestamp_prop.get("number")
        duration = duration_prop.get("number")
        if stamp is not None:
            if duration is not None and (not isinstance(duration, (int, float)) or duration < 0):
                raise ValueError("Invalid existing Notion reading duration")
            rows.append({
                "id": result["id"], "timestamp": stamp, "duration": duration,
            })
    return rows


def write_daily_record(helper, item):
    day = item["day"]
    stamp = item["timestamp"]
    seconds = item["seconds"]
    date = datetime.fromisoformat(day)
    local_date = date.strftime("%Y-%m-%d %H:%M:%S")
    props = {
        "标题": get_title(date.strftime("%Y年%m月%d日")),
        "日期": get_date(local_date),
        "时长": get_number(seconds),
        "时间戳": get_number(stamp),
        "年": get_relation([helper.get_year_relation_id(date)]),
        "月": get_relation([helper.get_month_relation_id(date)]),
        "周": get_relation([helper.get_week_relation_id(date)]),
    }
    if item.get("page_id"):
        helper.client.pages.update(page_id=item["page_id"], properties=props)
    else:
        helper.client.pages.create(
            parent=helper._parent(helper.day_database_id),
            properties=props,
            icon=get_icon("https://www.notion.so/icons/target_red.svg"),
        )


def main():
    from weread2notionpro.weread_api import WeReadApi
    from weread2notionpro.notion_helper import NotionHelper

    mode = os.getenv("READ_TIME_MODE", "preview").strip().lower()
    if mode not in ("preview", "import"):
        raise ValueError("READ_TIME_MODE must be preview or import")
    year = int(os.getenv("READ_TIME_YEAR") or datetime.now(TZ).year)
    if year < 2000 or year > datetime.now(TZ).year:
        raise ValueError("READ_TIME_YEAR must be between 2000 and the current year")

    # Must be set BEFORE helper construction, so preview never updates Settings.
    if mode == "preview":
        os.environ["NOTION_READ_ONLY"] = "true"
    api = WeReadApi()
    if not api.api_key:
        raise RuntimeError("READ_TIME_REQUIRES_API_KEY: Configure WEREAD_API_KEY")
    helper = NotionHelper()
    source_days = fetch_year_daily(api, year)
    existing = read_existing_days(helper)
    plan = daily_reconciliation(source_days, existing, year)
    print(
        f'READ_TIME_AUDIT: year={year} source_days={len(source_days)} '
        f'existing_rows={len(existing)} '
        f'create={len(plan["create"])} update={len(plan["update"])} '
        f'unchanged={plan["unchanged"]} preserved={plan["preserved"]}'
    )
    # Do not print daily reading time details: they are personal activity data.
    if mode == "preview":
        print("READ_TIME_PREVIEW_ONLY: no daily or related Notion records modified")
        return

    # All monthly periods, source records and existing records were validated.
    # Never delete old days, and never write zero-duration replacements.
    for item in plan["create"] + plan["update"]:
        write_daily_record(helper, item)
    print(
        f'READ_TIME_IMPORT_COMPLETED: created={len(plan["create"])} '
        f'updated={len(plan["update"])}'
    )


if __name__ == "__main__":
    main()
