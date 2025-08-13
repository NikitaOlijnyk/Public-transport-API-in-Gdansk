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
from typing import Callable, Optional

from app.utils.parse_time import parse_time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


load_dotenv()

# API_URL = os.getenv("API_URL", "https://ckan2.multimediagdansk.pl").rstrip("/")
# STOP_A = os.getenv("STOP_A", "")
# STOP_B = os.getenv("STOP_B", "")

API_URL_A = "https://ckan2.multimediagdansk.pl/departures?stopId=2101"
API_URL_B = "https://ckan2.multimediagdansk.pl/departures?stopId=2102"

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
TZ = ZoneInfo("Europe/Warsaw")

logger = logging.getLogger("ztm")
logging.basicConfig(level=logging.INFO)


_state_lock = asyncio.Lock()

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

class ZTMService:
    api_url: str
    data: list
    timeout: int
    formatter: Optional[Callable] = None
    
    def __init__(self, url: str,   http_client_factory: Callable[[], httpx.AsyncClient], timeout: int, formatter):
        self.api_url = url.rstrip("/")
        self.http_client_factory = http_client_factory
        self.timeout = timeout
        self.formatter = formatter
        self.error = False
        self._lock = asyncio.Lock()

    async def getData(self):
        try:
            async with self.http_client_factory(timeout = self.timeout) as client:
                resp = await client.get(self.api_url)
                resp.raise_for_status()
                payload = resp.json()
        except  Exception as e:
            print(f"Error {e}")
            async with self._lock:
                self.error = True
            return
    
        async with self._lock:
            self.error = False
            if self.formatter:
                self.data = [self.formatter(it) for it in payload.get("departures", [])]
            else:
                self.data = payload 

    async def getFormattedData(self):
        async with self._lock:
            return {
                "error": self.error,
                "data": self.data
            }

_route_a = ZTMService(API_URL_A, httpx.AsyncClient, 10, transform_departure_item)
_route_b = ZTMService(API_URL_B, httpx.AsyncClient, 10, transform_departure_item)

async def _update_once():
     await asyncio.gather(
        _route_a.getData(),
        _route_b.getData()
    )

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
        a = await _route_a.getFormattedData()
        b = await _route_b.getFormattedData()
    if a is None or b is None:
        return JSONResponse({"message": "data isn't loaded"}, status_code=503)
    if a.get("error") or b.get("error"):
        return JSONResponse({"message": "fetch error", "side_a": a, "side_b": b}, status_code=502)
    return {"side_a": a, "side_b": b}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    a = (await _route_a.getFormattedData())["data"]  or []
    b = (await _route_b.getFormattedData())["data"] or []
    return templates.TemplateResponse("index.html", {
        "request": request,
        "side_a": a,
        "side_b": b
    })
