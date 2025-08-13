# FastAPI Public Transport App

Public Transport Departures Monitor (Gdańsk ZTM API)

This project is a FastAPI-based application that periodically fetches and displays real-time public transport departure data from the Gdańsk ZTM API.

It polls two configured stops at regular intervals, stores the latest departure data in memory, and serves it via both JSON API endpoints and an HTML template.

## Features

- **Automatic polling** – Continuously fetches departure information for two predefined stops.
- **Configurable** – API URL, stop IDs, polling interval, and time zone can be set via `.env` file.
- **Time zone support** – Converts departure times to Europe/Warsaw.
- **Delay tracking** – Displays delays in seconds, if available.
- **Template rendering** – HTML interface with live departure lists.
- **REST API** – JSON endpoint for easy integration with other apps.

## 🧾 Example `.env` File

Create a `.env` file in the root of the project with the following content:

```env
API_URL=https://ckan2.multimediagdansk.pl
STOP_A=2101
STOP_B=2102
POLL_INTERVAL=60
```

🚀 How to Run the Project
### Use web
```bash
uvicorn main:app --reload --port 8000
```
### Use cli
```bash
python -m cli
```

## Running Tests

To run tests, make sure you are in the project root directory and use:

```bash
PYTHONPATH=. pytest
