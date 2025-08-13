
import os
import asyncio
import httpx
import typer
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.columns import Columns
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
DEFAULT_INTERVAL = max(20, int(os.getenv("CLI_INTERVAL", "20")))

console = Console()
app = typer.Typer(help="CLI do wyświetlania odjazdów z dwóch słupków")


def make_table(title: str, departures: list) -> Table:
    t = Table(title=title, show_header=True, header_style="bold magenta")
    t.add_column("Linia", width=8)
    t.add_column("Kierunek", width=30)
    t.add_column("Czas (Warsaw)", width=25)
    t.add_column("Opóźnienie", justify="right", width=12)
    for d in departures:
        delay = d.get("delay_seconds") or 0
        delay_label = "-" if delay == 0 else f"{delay//60}m {delay%60}s"
        style = "bold red" if delay >= 5*60 else ""
        t.add_row(str(d.get("line") or ""),
                  str(d.get("direction") or ""),
                  str(d.get("time_warsaw") or "-"),
                  delay_label,
                  style=style)
    return t


@app.command()
def watch(interval: int = DEFAULT_INTERVAL, combined: bool = False, host: str = API_URL):
    if interval < 20:
        console.print("[yellow]Interval must be >= 20s. Using 20s instead.[/yellow]")
        interval = 20

    async def _run():
        async with httpx.AsyncClient(timeout=10.0) as client:
            with Live(console=console, refresh_per_second=4) as live:
                while True:
                    try:
                        resp = await client.get(f"{host}/departures")
                        if resp.status_code == 200:
                            payload = resp.json()
                            a = payload.get("side_a", {}).get("data", []) or []
                            b = payload.get("side_b", {}).get("data", []) or []
                            if combined:
                                merged = sorted(a + b, key=lambda x: x.get("time_warsaw") or "")
                                tbl = make_table("Combined departures", merged)
                                live.update(tbl)
                            else:
                                left = make_table("Side A", a)
                                right = make_table("Side B", b)
                                cols = Columns([left, right], expand=True)
                                live.update(cols)
                        else:
                            live.update(f"[red]Fetch error {resp.status_code}[/red]")
                    except Exception as e:
                        live.update(f"[red]Exception: {e}[/red]")
                    await asyncio.sleep(interval)

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        console.print("\n[bold]Stopped[/bold]")


if __name__ == "__main__":
    app()
