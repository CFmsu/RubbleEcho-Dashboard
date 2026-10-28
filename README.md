# RubbleEcho

A person drives the sand-table rover from a phone. The laptop records what the Raspberry Pi sends. On a knock, a scrape, or radar presence, two NVIDIA models on Nebius Token Factory describe the frame and suggest the next check. The models do not move the car.

This is a practice console. It does not locate a buried person or report anyone as alive.

## Run

Laptop, first terminal:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8081
```

Second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173/`. On the phone, same Wi-Fi, open `http://<laptop-ip>:5173/#remote`.

Put the Nebius key only in `backend/.env`. Do not commit that file. Set `AI_ENABLED=true`, `NEBIUS_API_KEY`, `NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/`, `NEBIUS_MODEL_ID=nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`, and `NEBIUS_VISION_MODEL_ID=nvidia/Nemotron-3.5-Super-VL`.

If the rover shows up as a generic Bluetooth COM port, set `RUBBLEECHO_MOTOR_PORT` to that port and start the API again. Do not point it at a radar port.

## Drive

The phone page has Start, Stop, four arrows, and On/Off for Radar, Range, Mic, and Cam.

- **Start** opens the live session on the laptop. The car stays still.
- Hold an arrow. The laptop sends `F`, `B`, `L`, or `R` to the Uno at 9600 baud. Release sends `S`. The Uno also stops about one second after the last character.
- **Stop** sends `S`.
- **Off** skips that sensor. Mic Off stops the laptop microphone. Radar Off stops the radar reader.

## Record

The Pi posts to `http://<laptop-ip>:8081/api/pi/ingest`:

```json
{
  "radar": {},
  "ultrasonic": {},
  "encoders": {},
  "lines": [],
  "camera_jpeg_base64": ""
}
```

A knock, a scratch/scrape, or radar presence marks the heatmap and stores a report. If Cam is On and a JPEG was posted, the vision model describes that frame, then the reasoning model suggests the next check. Neither call drives the motors.

The scripted demo is a separate button on the laptop. It does not move the rover, and it rejects Pi posts while it is running.

Diagnostics shows a device connected only after a real sample. One camera is on the live page. Acoustic classes from the USB mic are local shape rules, not the NVIDIA model.

## Check

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm run lint
```

## License

MIT. See `LICENSE`.
