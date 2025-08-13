import os
import asyncio
import logging
from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo
from fastapi.templating import Jinja2Templates
from fastapi import Request
import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from dotenv import load_dotenv

from app.utils.parse_time import parse_time_to_warsaw

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


load_dotenv()

API_URL = os.getenv("API_URL", "https://ckan2.multimediagdansk.pl").rstrip("/")
STOP_A = os.getenv("STOP_A", "")
STOP_B = os.getenv("STOP_B", "")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
TZ = ZoneInfo("Europe/Warsaw")

logger = logging.getLogger("ztm")
logging.basicConfig(level=logging.INFO)

_route_a = None
_route_b = None
_state_lock = asyncio.Lock()

def transform_departure_item(item: dict) -> dict:
    est = item.get("estimatedTime") or item.get("estimated_time") or item.get("theoreticalTime")
    dt_local = parse_time_to_warsaw(est, TZ)
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


async def fetch_departures_for_stop(stopid: str) -> dict:
    url = f"{API_URL}/departures?stopId={stopid}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        logger.exception("Fetch failed for %s: %s", stopid, exc)
        return {"stopid": stopid, "error": True, "data": None, "lastUpdate": None}
    items = payload.get("departures") if isinstance(payload, dict) else []
    transformed = [transform_departure_item(it) for it in items]
    return {
        "stopid": stopid,
        "error": False,
        "lastUpdate": payload.get("lastUpdate"),
        "data": transformed
    }


async def _update_once():
    global _route_a, _route_b
    a = await fetch_departures_for_stop(STOP_A)
    b = await fetch_departures_for_stop(STOP_B)
    async with _state_lock:
        _route_a = a
        _route_b = b
    logger.info("Updated stops %s and %s", STOP_A, STOP_B)


async def polling_loop():
    while True:
        try:
            await _update_once()
        except Exception:
            logger.exception("Unhandled error in polling loop")
        await asyncio.sleep(POLL_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(polling_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)


@app.get("/departures")
async def get_departures():
    async with _state_lock:
        a = _route_a
        b = _route_b
    if a is None or b is None:
        return JSONResponse({"message": "data isn't loaded"}, status_code=503)
    if a.get("error") or b.get("error"):
        return JSONResponse({"message": "fetch error", "side_a": a, "side_b": b}, status_code=502)
    return {"side_a": a, "side_b": b}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    a = _route_a["data"] if _route_a and not _route_a.get("error") else []
    b = _route_b["data"] if _route_b and not _route_b.get("error") else []
    return templates.TemplateResponse("index.html", {
        "request": request,
        "side_a": a,
        "side_b": b
    })
