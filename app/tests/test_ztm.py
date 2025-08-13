# test_ztm.py
from datetime import datetime
from zoneinfo import ZoneInfo
from app.services import ztm

TZ = ZoneInfo("Europe/Warsaw")


def test_parse_time_to_warsaw_utc():
    iso_utc = "2025-08-13T12:00:00Z"
    dt = ztm.parse_time_to_warsaw(iso_utc)
    assert dt.tzinfo == TZ
    assert dt.hour == 14 

def test_parse_time_to_warsaw_local_offset():
    iso_local = "2025-08-13T12:00:00+02:00"
    dt = ztm.parse_time_to_warsaw(iso_local)
    assert dt.tzinfo == TZ
    assert dt.hour == 12


def test_parse_time_to_warsaw_none_or_invalid():
    assert ztm.parse_time_to_warsaw("") is None
    assert ztm.parse_time_to_warsaw(None) is None
    assert ztm.parse_time_to_warsaw("invalid") is None


def test_transform_departure_item_basic():
    item = {
        "routeShortName": "10",
        "headsign": "Downtown",
        "estimatedTime": "2025-08-13T12:00:00Z",
        "delayInSeconds": "120"
    }
    result = ztm.transform_departure_item(item)
    assert result["line"] == "10"
    assert result["direction"] == "Downtown"
    assert result["time_warsaw"] is not None
    assert result["delay_seconds"] == 120
    assert result["raw"] == item


def test_transform_departure_item_missing_fields():
    item = {}
    result = ztm.transform_departure_item(item)
    assert result["line"] == ""
    assert result["direction"] == ""
    assert result["time_warsaw"] is None
    assert result["delay_seconds"] == 0
    assert result["raw"] == item