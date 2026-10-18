# RubbleEcho

A search-and-rescue rover simulation dashboard developed for the ACM 2026 hackathon.

## Project Overview

RubbleEcho demonstrates a rover concept designed to explore an area, knock on a surface, listen for possible responses, evaluate simulated observations, and select the next location to investigate.

The project provides a web dashboard for viewing mission status, rover position, probe locations, telemetry, events, and confidence estimates.

**Important:** This is a software simulation. It does not locate real people, control connected rover hardware, or provide verified rescue information.

## How It Works

The project consists of two main parts:

- **Frontend:** A React and TypeScript dashboard built with Vite.
- **Backend:** A Python FastAPI application that manages the simulated mission and provides API endpoints and WebSocket telemetry.

The frontend communicates with the backend to display mission information and controls. The hidden source coordinate remains on the server and is not included in API or telemetry responses.

## Project Structure

- `backend/` — API, simulation logic, dependencies, and backend tests.
- `frontend/` — React dashboard, components, mission controls, and telemetry connection.
- `docs/` — Project presentation talk track.

## Running the Project

### 1. Start the backend

Open a terminal from the repository root:

```bash
cd backend
py -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8081
```

Keep the backend terminal running.

### 2. Start the frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite.

The frontend proxy and WebSocket connection should target the port on which the backend is running. This project currently uses port `8081`.

### 3. Run backend tests

From the repository root, run:

```bash
backend/.venv/Scripts/python.exe -m pytest backend/test_main.py -q
```

## Safety and Limitations

RubbleEcho is a simulation prototype. The displayed rover position, probe locations, events, and confidence estimates represent simulated results, not verified field measurements. No physical rover, knocker, microphone, or vibration sensor is connected. This software must not be used to make real-world rescue decisions.
