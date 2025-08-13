import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.presentation.handler import polling_loop
from app.presentation import handler

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

app.include_router(handler.router)