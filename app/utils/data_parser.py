from zoneinfo import ZoneInfo
from app.utils.parse_time import parse_time

TZ = ZoneInfo("Europe/Warsaw")


def transform_departure_item(item: dict) -> dict:
    est = item.get("estimatedTime") or item.get("estimated_time") or item.get("theoreticalTime")
    dt_local = parse_time(est, TZ)
    delay = item.get("delayInSeconds")
    try:
        delay = int(delay) if delay is not None else 0
    except Exception:
        delay = 0
    return {
        "line": item.get("routeShortName") or item.get("route_short_name") or item.get("route") or "",
        "direction": item.get("headsign") or item.get("destination") or "",
        "time_warsaw": dt_local.isoformat() if dt_local else None,
        "delay_seconds": delay,
        "raw": item
    }