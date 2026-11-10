"""Render WeRead's *actual* Notion daily totals into an SVG heatmap.

Does not estimate per-book reading history. Safe for offline tests.
"""
import calendar
from datetime import date, datetime, timedelta, timezone
from math import isfinite
from xml.etree.ElementTree import Element, SubElement, tostring

TZ = timezone(timedelta(hours=8))

COLORS = ("#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39")


def year_days(year):
    d = date(year, 1, 1)
    end = date(year + 1, 1, 1)
    while d < end:
        yield d
        d += timedelta(days=1)


def seconds_color(seconds):
    if not isinstance(seconds, (int, float)) or not isfinite(seconds) or seconds < 0:
        raise ValueError("Reading duration must be nonnegative finite seconds")
    if seconds == 0:
        return COLORS[0]
    if seconds < 300:
        return COLORS[1]
    if seconds < 1800:
        return COLORS[2]
    if seconds < 3600:
        return COLORS[3]
    return COLORS[4]


def days_from_notion_rows(rows, year):
    """Return date -> seconds, rejecting conflicting duplicate positive records."""
    by_day = {}
    existing = 0
    duplicates = 0
    for row in rows:
        props = row.get("properties") or {}
        stamp = (props.get("时间戳") or {}).get("number")
        amount = (props.get("时长") or {}).get("number")
        if stamp is None:
            continue
        if not isinstance(stamp, (float, int)) or not isfinite(stamp):
            raise ValueError("Invalid reading-day timestamp in Notion")
        d = datetime.fromtimestamp(stamp, TZ).date()
        if d.year != year:
            continue
        existing += 1
        if amount is None:
            continue
        if not isinstance(amount, (int, float)) or not isfinite(amount) or amount < 0:
            raise ValueError("Invalid daily reading duration in Notion")
        value = int(amount)
        if d in by_day:
            duplicates += 1
            if value and by_day[d] and value != by_day[d]:
                raise ValueError("Conflicting Notion daily entries on " + d.isoformat())
            by_day[d] = max(by_day[d], value)
        else:
            by_day[d] = value
    return by_day, existing, duplicates


def render_svg(year, duration_by_date):
    if year < 2000 or year > 2098:
        raise ValueError("Unsupported year")
    for day, seconds in duration_by_date.items():
        if not isinstance(day, date) or day.year != year:
            raise ValueError("Heatmap day lies outside requested year")
        seconds_color(seconds)

    jan1 = date(year, 1, 1)
    monday = jan1 - timedelta(days=jan1.weekday())
    final = date(year, 12, 31)
    weeks = ((final - monday).days // 7) + 1
    left, top, unit, side = 45, 51, 14, 11
    width, height = left + weeks * unit + 18, 183
    root = Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "width": str(width), "height": str(height),
        "viewBox": f"0 0 {width} {height}",
        "role": "img", "aria-label": f"{year} daily WeRead reading time heatmap",
    })
    SubElement(root, "rect", {"width":str(width),"height":str(height),"fill":"#fff"})
    title=SubElement(root, "text", {"x":str(left),"y":"20","fill":"#24292f",
                                       "font-size":"16","font-family":"Arial, sans-serif"})
    title.text=f"{year} 年阅读热力图"
    for month in range(1,13):
        first=date(year,month,1)
        w=(first-monday).days//7
        el=SubElement(root,"text",{"x":str(left+w*unit),"y":"40",
                                    "font-size":"10","fill":"#57606a"})
        el.text=f"{month}月"
    for weekday,label in ((0,"一"),(2,"三"),(4,"五")):
        el=SubElement(root,"text",{"x":"22","y":str(top+weekday*unit+9),
                                    "font-size":"10","fill":"#57606a"})
        el.text=label
    for day in year_days(year):
        index=(day-monday).days
        col,row=divmod(index,7)
        sec=duration_by_date.get(day,0)
        cell=SubElement(root,"rect",{
            "x":str(left+col*unit),"y":str(top+row*unit),
            "width":str(side),"height":str(side),"rx":"2",
            "fill":seconds_color(sec),
            "data-date":day.isoformat(),
        })
        tip=SubElement(cell,"title")
        hours,rem=divmod(int(sec),3600)
        mins,seconds=divmod(rem,60)
        tip.text=f"{day.isoformat()} · {hours}小时{mins}分{seconds}秒"
    legend=SubElement(root,"text",{"x":str(left),"y":"166",
                                    "fill":"#57606a","font-size":"11"})
    count=sum(1 for x in duration_by_date.values() if x>0)
    legend.text=f"有记录的阅读日：{count}  ｜  浅色：时间较少；深色：时间较长"
    return tostring(root, encoding="unicode", xml_declaration=True)
