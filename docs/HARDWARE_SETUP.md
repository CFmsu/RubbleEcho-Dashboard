# Hardware setup

Nothing in this file was run on a Raspberry Pi from the Windows session that wrote it. Commands below are the ones to run on each machine. A missing device stays disconnected.

## Windows, simulation only

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:OPERATOR_TOKEN = "choose-a-local-token"
$env:AI_ENABLED = "false"
uvicorn main:app --reload --port 8081
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL. Choose Load replay after the operator token is saved in Diagnostics. That replay is a labeled fixture, not a live rover.

Mock envelopes, with null measurements:

```powershell
python tools\mock_pi\mock_raspberry_pi.py
```

## Raspberry Pi 4

Clone the same repository on the Pi. Use a virtual environment. Do not replace the OS OpenCV packages blindly. Picamera2 comes from Raspberry Pi OS:

```bash
sudo apt install python3-picamera2
rpicam-hello --list-cameras
arecord -l
ls /dev/serial/by-id/
```

Record a check clip only after `arecord -l` shows the XVF3800 card number. Do not assume four raw channels. Use the channel count the firmware actually exposes.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPERATOR_TOKEN=choose-a-local-token
export AI_ENABLED=false
uvicorn main:app --host 0.0.0.0 --port 8081
```

Bind that port only on a trusted LAN. Movement and knock routes require `X-Operator-Token`. The browser on a laptop uses the Pi address as the API host.

Arduino sketches in `firmware/` are uploaded with the Arduino IDE. Pin numbers in those sketches are a starting map, not a surveyed wiring sheet, until someone checks them on the bench. The motor driver in this tree is the Cytron MDD10A path already used by the Uno sketch. Do not power two motors from one channel until the current limit is checked.

`RUBBLEECHO_PROBE_CAMERAS=1` is the only switch that asks OpenCV to look for a camera. Leave it at 0 on a machine with no camera.

## One camera

The live page shows one camera. It is disconnected until a frame is captured. There is no 360 degree claim.
