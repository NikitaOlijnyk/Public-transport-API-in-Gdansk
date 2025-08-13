import os
import logging
import asyncio
from dotenv import load_dotenv
from fastapi.responses import JSONResponse, HTMLResponse
import httpx

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from app.services.ztm import ZTMService
from app.utils.data_parser import transform_departure_item


load_dotenv()

API_URL = os.getenv("API_URL", "https://ckan2.multimediagdansk.pl")
STOP_A = os.getenv("STOP_A", "")
STOP_B = os.getenv("STOP_B", "")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))

router = APIRouter()


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


query_a = f"departures?stopId={STOP_A}"
query_b = f"departures?stopId={STOP_B}"


logger = logging.getLogger("ztm")
logging.basicConfig(level=logging.INFO)


_state_lock = asyncio.Lock()

_route_a = ZTMService(API_URL, httpx.AsyncClient, 10, transform_departure_item)
_route_b = ZTMService(API_URL, httpx.AsyncClient, 10, transform_departure_item)

async def _update_once():
     await asyncio.gather(
        _route_a.getData(query_a),
        _route_b.getData(query_b)
    )

async def polling_loop():
    while True:
        try:
            await _update_once()
        except Exception:
            logger.exception("Unhandled error in polling loop")
        await asyncio.sleep(POLL_INTERVAL)

@router.get("/departures")
async def get_departures():
    async with _state_lock:
        a = await _route_a.getFormattedData()
        b = await _route_b.getFormattedData()
    if a is None or b is None:
        return JSONResponse({"message": "data isn't loaded"}, status_code=503)
    if a.get("error") or b.get("error"):
        return JSONResponse({"message": "fetch error", "side_a": a, "side_b": b}, status_code=502)
    return {"side_a": a, "side_b": b}


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    a = (await _route_a.getFormattedData())["data"]  or []
    b = (await _route_b.getFormattedData())["data"] or []
    return templates.TemplateResponse("index.html", {
        "request": request,
        "side_a": a,
        "side_b": b
    })
