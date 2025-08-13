from datetime import datetime, timezone

def parse_time(timestr: str, tz):
    if not timestr:
        return None
    try:
        if timestr.endswith("Z"):
            iso = timestr[:-1] + "+00:00"
        else:
            iso = timestr
        dt = datetime.fromisoformat(iso)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)