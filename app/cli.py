
import asyncio
import httpx
from rich.console import Console
from rich.table import Table

API_LOCAL = "http://127.0.0.1:8000/departures"
REFRESH_INTERVAL = 20

console = Console()

def render_table(side_name, data):
    table = Table(title=f"Side {side_name}", expand=True)
    table.add_column("Linia", style="bold cyan")
    table.add_column("Kierunek", style="bold magenta")
    table.add_column("Czas (Warsaw)", style="bold yellow")
    table.add_column("Opóźnienie", justify="right", style="bold red")
    for dep in data.get("data", []):
        table.add_row(
            dep.get("line", ""),
            dep.get("direction", ""),
            dep.get("time_warsaw", ""),
            str(dep.get("delay_seconds", ""))
        )
    return table

async def main():
    async with httpx.AsyncClient() as client:
        while True:
            try:
                resp = await client.get(API_LOCAL, timeout=10)
                resp.raise_for_status()
                payload = resp.json()
            except Exception as e:
                console.print(f"[red]Error fetching departures: {e}[/red]")
                await asyncio.sleep(REFRESH_INTERVAL)
                continue

            console.clear()
            side_a = payload.get("side_a", {})
            side_b = payload.get("side_b", {})

            console.print(render_table("A", side_a))
            console.print(render_table("B", side_b))

            await asyncio.sleep(REFRESH_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
