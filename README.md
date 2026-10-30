# RubbleEcho

RubbleEcho is a sand-table search rover and operator console for the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/), **Physical AI** track.

A person drives the rover from a phone. A Raspberry Pi reads the range sensors and posts them to a laptop. After the rover has covered the nine squares, two NVIDIA open models on [Nebius Token Factory](https://tokenfactory.nebius.com/) read that evidence and name the square to check first. The models never command the motors.

This is a research testbed on a measured sand table. It does not locate a buried person and it does not report anyone as alive.

License: MIT (`LICENSE`).

## What it does

1. The phone remote holds the rover on a heading, sets motor speed, aims the two sensor servos, and can deploy or collect a reading.
2. **Arm rover** sends one start character. The Arduino then drives a fixed nine-square snake. The first square is a 12-second listen. Straight squares keep rolling. The rover turns only at the corners.
3. The Pi posts ultrasonic range, 60 GHz radar, and any camera frame to the laptop. The sand-table map moves with the rover.
4. When the ninth square is done, the laptop asks Nebius Token Factory to reason over the stored cells, then draws the heatmap.
5. **STOP** sends a stop character and ends the session. A hardware power cut is still the real e-stop.

## Track fit

| Requirement | How this project meets it |
| --- | --- |
| Nebius Token Factory | Runtime chat calls to `https://api.tokenfactory.nebius.com/v1/`. |
| NVIDIA open model | Reasoning: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`. Vision, when a JPEG is posted: `nvidia/Nemotron-3.5-Super-VL`. |
| Physical AI | The rover, the Pi, and the Uno are the body. The models only advise. |
| Open source | MIT license at the repository root. |

A hosted demo URL is not required for Physical AI. The demonstration video must be public on YouTube, under three minutes, and include at least one minute of the rover actually moving.

## Architecture

```text
phone browser  ----Wi-Fi---->  laptop dashboard (Vite :5173)
                                    |
                                    |  /api and /ws proxy
                                    v
                               FastAPI (:8081)
                                    |
                    +---------------+---------------+
                    |                               |
                    |  command queue                |  Token Factory
                    v                               v
            Raspberry Pi sweep.py            Nemotron Nano  (text)
                    |                        Nemotron Super VL (JPEG)
         +----------+----------+
         |                     |
    Arduino Uno             GPIO
    L298N + wheels          ultrasonic, two servos
                            60 GHz radar on USB
```

The laptop does not open the motor port while the Pi owns the Uno USB cable. Drive letters and speed digits sit in a queue. Servo, deploy, and collect jobs sit in a second queue. `tools/pi_capture/sweep.py` on the Pi polls both, writes motor bytes to the Uno, and moves the servos itself.

Reasoning is a JSON review of evidence already stored. It cannot set PWM, pins, or a motor command. Every recommendation still needs a person.

## Hardware

| Part | Role |
| --- | --- |
| Sand table, Rev C | 105 cm by 80 cm outer footprint. Nine cells. Geometry is `shared/config/sand_table_rev_c.json`. |
| Raspberry Pi 5 | Sensor host and the only computer that should hold the Uno USB cable during a run. |
| Arduino Uno + L298N | Wheel driver only. Sketch: `firmware/arduino_uno_motor_encoder/`. |
| DG01D gearmotors | Left and right drive. Both H-bridge channels use the same pin polarity. |
| HC-SR04 ultrasonic | Forward range. Wired to the Pi, not the Uno. |
| Two hobby servos | One aims the ultrasonic. One aims the radar. They stay still until the remote holds a direction. |
| 60 GHz mmWave (MR60BHA2 class) | Presence and range over USB to the Pi. |
| Microphone | Acoustic class (knock, scrape, room) is computed on the laptop from the posted window. |
| Laptop | Dashboard, API, and the Token Factory client. |
| Phone | Same network as the laptop. Opens the remote page. |
| Common ground | Pi, Uno supply, ultrasonic, and both servos share ground. |

### Pi wiring

BCM numbers are the GPIO numbers.

| Signal | BCM | Physical pin |
| --- | --- | --- |
| Ultrasonic servo | 18 | 12 |
| mmWave servo | 19 | 35 |
| Ultrasonic trigger | 23 | 16 |
| Ultrasonic echo | 24 | 18 |

Ultrasonic VCC uses a Pi 5V pin (physical pin 2 or 4). Feed that pin to the breadboard red rail. The ultrasonic and both servo power wires share that rail. All grounds share the blue rail back to any Pi ground.

Echo is 5 V. Divide it: Echo — 1 kΩ — GPIO 24 — 2 kΩ — GND. Trigger has no resistors.

Servo angles: 90 is forward, 0 is the rover's left, 180 is the rover's right. Two servos on the Pi 5 V rail can brown the Pi out. If a horn keeps moving and the Pi drops off the network, pull the servo signal wires (GPIO 18 and GPIO 19) or the shared 5 V feed.

### Uno wiring

| Signal | Pin |
| --- | --- |
| ENA (left PWM) | D5 |
| IN1, IN2 | D8, D9 |
| IN3, IN4 | D10, D11 |
| ENB (right PWM) | D6 |
| Software serial RX, TX | D2, D3 at 9600 |

The grid path uses full PWM. Manual arrows use the remote speed digit (0–9 maps to 0–255). A digit of 0 stops. Unguided motion also stops about 1.6 seconds after the last character, so the remote repeats the held arrow.

### Nine squares

Visit order, east at the start:

`r1c1 → r1c2 → r1c3 → r2c3 → r2c2 → r2c1 → r3c1 → r3c2 → r3c3`

Named sites sit on some of those cells (`A_NEAR` on the second square, and the far and near marks for A, B, and C). The heatmap is withheld until reasoning for the full grid has finished.

## Software

| Layer | Stack |
| --- | --- |
| Dashboard | React 19, TypeScript, Vite, Tailwind CSS |
| API | Python 3.12, FastAPI, Uvicorn, Pydantic, httpx |
| Serial | pyserial. The Pi opens the Uno. The laptop queues commands. |
| Signal math | NumPy, SciPy. Acoustic class is a local shape rule, not the NVIDIA model. |
| Pi agent | `tools/pi_capture/sweep.py` (Python 3, gpiozero, pyserial). The Pi user needs the `gpio` and `dialout` groups. |
| Firmware | Arduino Uno sketch. Flash with Arduino CLI or the IDE, board `arduino:avr:uno`. |
| Models | Nebius Token Factory, OpenAI-compatible chat completions. |
| Tests | pytest. Frontend lint is ESLint. |

## Models

Put the key only in `backend/.env`. Never commit that file.

```text
AI_ENABLED=true
NEBIUS_API_KEY=
NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1/
NEBIUS_MODEL_ID=nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B
NEBIUS_VISION_MODEL_ID=nvidia/Nemotron-3.5-Super-VL
```

`NEBIUS_MODEL_ID` writes the cell narrative and the next square to check. `NEBIUS_VISION_MODEL_ID` describes a JPEG only when the Pi posted one. Neither call is allowed to move the rover. If the key is missing, the dashboard still runs and the model row stays unconfigured.

## Run

The phone, the laptop, and the Pi must be on one network. An iPhone hotspot has no mDNS, so use the laptop's hotspot IP and port, for example `http://172.20.10.4:5173`. Do not use `https` for that page. `raspberrypi.local` will not resolve on that hotspot.

Laptop, first terminal:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8081
```

Fill `backend/.env` before you expect a model call. Leave `RUBBLEECHO_SERIAL_PORT` empty when the Uno is plugged into the Pi. If the Uno is plugged into the laptop instead, set that variable to the Uno's COM port (an Uno enumerates as VID `2341`, PID `0043`). Do not point it at the radar's USB port.

Second terminal:

```powershell
cd frontend
npm install
npx vite --host 0.0.0.0 --port 5173
```

Open `http://localhost:5173/` on the laptop. On the phone, open `http://<laptop-ip>:5173/#remote`.

On the Pi, from the Pi user's Desktop copy of the sweep script:

```bash
python3 -u ~/Desktop/sweep.py http://<laptop-ip>:5173
```

The script rewrites an `https` dashboard URL to `http`. Leave it running. It forwards `F`, `B`, `L`, `R`, `S`, speed digits, and cell lines to the Uno, and it applies servo, deploy, and collect jobs locally.

### Remote

- Hold an arrow to drive. Release sends `S`.
- Motor speed is 0–9. Set it before the first arrow so the digit is queued first.
- Ultrasonic and mmWave each have Left, Center, and Right, plus a speed. Center creeps toward 90. Release detaches the servo so it does not keep hunting.
- **Deploy** listens on the first square without driving.
- **Collect signal** reads ultrasonic, radar, and a short microphone window.
- **Manual** is the arrow path. **Auto** rejects drive letters other than stop while a grid is in charge.

### Arm and stop

**Arm rover** asks for confirmation, then sends `A`. The firmware always restarts the snake at row 1, square 1, even if the rover was left somewhere else. Put it back on that square, facing the second square, before you confirm.

**STOP** sends `S` through the same queue. If the sweep script is running, the wheels stop.

## Check

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm run lint
```

## Repository map

| Path | What it is |
| --- | --- |
| `frontend/` | Operator dashboard and phone remote. |
| `backend/app/api/` | HTTP and WebSocket routes. |
| `backend/app/ai/` | Token Factory client, prompts, and the reasoning validator. |
| `backend/app/services/` | Grid, ingest, remote drive, and the mission session. |
| `backend/app/drivers/` | Serial, radar, ultrasonic, and microphone adapters. |
| `firmware/arduino_uno_motor_encoder/` | Wheel sketch. |
| `tools/pi_capture/sweep.py` | Pi process. Copy this file to the Pi. |
| `tools/pi_capture/stop_servos.py` | Releases GPIO 18 and 19 if a horn is still moving. |
| `shared/config/sand_table_rev_c.json` | Table geometry. |
| `backend/.env.example` | Variable names only. |

Captured trials, local databases, and `.env` are gitignored. Do not commit a key, a trial export, or a filled environment file.

## Submission

Submit at [nebiusglobalaihackathon.devpost.com](https://nebiusglobalaihackathon.devpost.com/). The deadline is **Friday, October 30, 2026, 10:00 AM Pacific**. After that, the form, the video, and this repository should stay as submitted.

Use this as the project text:

> RubbleEcho is a physical sand-table rover for a search-and-rescue research setup. An operator drives it from a phone. A Raspberry Pi reads an ultrasonic ranger and a 60 GHz radar while an Arduino Uno drives the wheels through an L298N. After nine squares, the laptop calls Nebius Token Factory. NVIDIA Nemotron 3 Nano writes the cell review, and Nemotron 3.5 Super VL describes a camera frame when one was posted. The models cannot move the rover. The heatmap appears only after that review.

Feedback worth sending with the form:

- Token Factory's OpenAI-compatible chat endpoint was enough. No extra SDK was required.
- Nano is the right size for a JSON review of nine short sensor cells. Super VL is reserved for a posted JPEG so the text call stays fast.
- The validator rejects motor, pin, and voltage fields, so a model reply cannot become a drive command.
- A missing or slow catalog check should leave the dashboard usable. This project does that: the rover path does not wait on the model.

Still required on the form, and not stored in this repository:

- A public YouTube video under three minutes, with at least one minute of the rover moving, plus a short look at the dashboard after the model review.
- Teammates invited on the form, each of whom has accepted.
- The public GitHub URL of this repository.
