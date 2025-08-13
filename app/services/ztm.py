import asyncio
import httpx
from typing import Callable, Optional



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

