import asyncio
import os
import httpx
from fastapi import FastAPI
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

API_URL=os.getenv("API_URL")



route_data_side_a = None
route_data_side_b = None



async def fetch_departures(url:str, query:str):
    api_url = url + query
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(api_url)
            response.raise_for_status()
            latest_data = response.json()
            print(f"Data update: {latest_data}")
            return {"data": latest_data, "error": False}
        except Exception as e:
            print(f"Error in taked data: {e}")
            return {"data": None, "error": True}

get_data_route_a = lambda: fetch_departures(API_URL, "/departures?stopid=2101")
get_data_route_b = lambda: fetch_departures(API_URL, "/departures?stopid=2102")



async def polling_loop():
    global route_data_side_b, route_data_side_a
    while True:
        route_data_side_a =  await get_data_route_a()
        route_data_side_b =  await get_data_route_b()
        await asyncio.sleep(60)



@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(polling_loop())
    yield
    task.cancel()

app = FastAPI(lifespan=lifespan)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(polling_loop())


@app.get("/departures")
async def get_departures():
    if route_data_side_b is None or route_data_side_a is None:
        return {"message": "data is'nt loaded"}
    if ("error" in route_data_side_b and route_data_side_b["error"])  or ("error" in route_data_side_a and route_data_side_a["error"]):
        return {"message": "data is failed"}
    return {"data": {
        "side_a": route_data_side_a,
        "side_b": route_data_side_b
    }}
