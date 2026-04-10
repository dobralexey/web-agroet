from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder


def get_utc_offset(lat: float, lng: float, dt: datetime = None) -> float:
    """Get UTC offset using zoneinfo (Python built-in)."""
    tf = TimezoneFinder()
    timezone_name = tf.timezone_at(lng=lng, lat=lat)

    if timezone_name is None:
        raise ValueError(f"No timezone found for ({lat}, {lng})")

    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Use Python's built-in zoneinfo
    tz = ZoneInfo(timezone_name)
    dt_tz = dt.astimezone(tz)
    offset = dt_tz.utcoffset()
    offset_minutes = offset.total_seconds() / 60
    offset_hours = offset_minutes / 60

    return offset_hours