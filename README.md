# RubbleEcho

RubbleEcho is a sand-table search rover and operator console for the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/), **Physical AI** track.

A person drives the rover from a phone. A Raspberry Pi reads the ultrasonic ranger, the 60 GHz radar, the acoustic array, and a camera frame when one is posted. After the rover has covered the nine squares, two NVIDIA open models on [Nebius Token Factory](https://tokenfactory.nebius.com/) read that evidence and name the square to check first. The models never command the motors.

This is the final project state for submission. The acoustic array is on the rover. It was tested, and the recordings from those tests are what the laptop classifies. A camera frame is used when one is available. This remains a research testbed on a measured sand table. It does not locate a buried person and it does not report anyone as alive.

License: MIT (`LICENSE`).

## What it does

1. The phone remote holds the rover on a heading, sets motor speed, aims the two sensor servos, and can deploy or collect a reading.
2. **Arm rover** sends one start character. The Arduino then drives a fixed nine-square snake. The first square is a 12-second listen. Straight squares keep rolling. The rover turns only at the corners.
3. The Pi posts ultrasonic range, 60 GHz radar, the acoustic-array window, and a camera frame when the camera has one. The sand-table map moves with the rover.
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
    Arduino Uno             GPIO and USB
    L298N + wheels          ultrasonic, two servos
                            60 GHz radar
                            acoustic array
                            camera, when a frame is posted
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
| Acoustic array | On the rover. Tested in the sand-table runs. The Pi records it and the laptop classifies the window. |
| Camera | Used when a frame is available. A posted JPEG is stored with that square and can be described by the vision model. |
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

## Audio processing

The acoustic array is part of the rover. During testing it was recorded on the Pi and those windows were gathered with the other cell readings.

On a listen, `tools/pi_capture/sweep.py` records with `arecord`: 16 kHz, 16-bit, about seven seconds, using the array device ALSA exposes (one or two channels, whichever that device accepts). The samples are normalized and posted to `POST /api/pi/ingest` with the ultrasonic reading and the radar frame for that square.

The laptop does not treat a missing window as a silent cell, and it does not invent a class when samples arrived. `classify_window` in `backend/app/services/feature_extraction.py` scores the posted digital audio:

- Peak level, RMS, and the fraction of samples above 0.1 decide the class.
- A sharp peak with few loud samples is a **knock**.
- A lower peak that stays loud across the window is a **scratch/scrape**.
- A very small peak and RMS is **silence**. A quiet but present window is **ambient**.
- A spectral centroid is stored with the class. Levels are dBFS, digital full scale, not sound-pressure level.
- The class is uncalibrated. It does not claim the sound came from under the sand, and it does not label speech.

The same module can process a four-channel block when one is supplied: a 50–4000 Hz Butterworth bandpass, a 256-sample Hann window hopping every 4 ms, and GCC-PHAT delay between capsules. That path measures arrival delay across the array. It does not turn a delay into a buried-person bearing.

The dashboard draws the waveform and the class for the square. After all nine squares, Nemotron repeats that class in the cell narrative. The model does not replace the classifier.

## Camera

The camera is used when a frame is available. The Pi posts `camera_jpeg_base64` with the cell. The laptop stores that JPEG on the square and shows it on the camera panel. If no frame was posted, the panel waits. It does not invent a picture.

When a frame is stored and `NEBIUS_VISION_MODEL_ID` is set, Nemotron 3.5 Super VL describes that JPEG. The description is evidence for the square. It is not a motor command. A connected camera that has posted a frame is shown as live.

## Software

| Layer | Stack |
| --- | --- |
| Dashboard | React 19, TypeScript, Vite, Tailwind CSS |
| API | Python 3.12, FastAPI, Uvicorn, Pydantic, httpx |
| Serial | pyserial. The Pi opens the Uno. The laptop queues commands. |
| Signal math | NumPy, SciPy. The acoustic class is computed on the laptop from the array window. Nemotron repeats that class. It does not replace it. |
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

`NEBIUS_MODEL_ID` writes the cell narrative and the next square to check. It includes the acoustic class that was measured. `NEBIUS_VISION_MODEL_ID` describes a JPEG when the camera posted one. Neither call is allowed to move the rover. If the key is missing, the dashboard still runs and the model row stays unconfigured. The array recording and the camera store do not wait on that key.

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
- **Collect signal** reads ultrasonic, radar, and a window from the acoustic array.
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

## Team

McNeese State University. RubbleEcho for the Nebius x NVIDIA Global AI Hackathon, Physical AI track.

| Name | Role | Major | Contact |
| --- | --- | --- | --- |
| Prince Pudasaini | Team lead | Computer Science, Artificial Intelligence | [LinkedIn](https://www.linkedin.com/in/prince-pudasaini/) |
| Dipendra Kandel | Co-leader | BE Mechanical Engineering | [LinkedIn](https://www.linkedin.com/in/dipendra-kandel-2995532b8/) |
| Arjun Gautam | | ME Civil Engineering | |
| Pratik Thapa | | BE Civil Engineering | [LinkedIn](https://www.linkedin.com/in/pratik-thapa-8ba5b63a9/) |
| Cooper Tadlock | | BS Computer Engineering | |
| Caden Fontenot | | BS Computer Science | |
| Pratikshya Parajuli | | BS Computer Science | |
| Rajesh Karki | | BS Computer Science, Artificial Intelligence | [LinkedIn](https://www.linkedin.com/in/rajesh-karki-232502283/) |
| Yuni Lin | | BS Computer Science | |

## Upgradability

The rover, the sensor posts, and the model calls are separate, so a later change does not have to replace the car.

- **Another Nemotron, or a newer NVIDIA open model.** Set `NEBIUS_MODEL_ID` and `NEBIUS_VISION_MODEL_ID`. The motor queue is unchanged. The validator still rejects voltage, PWM, and pin fields.
- **A camera that is always mounted.** Post each JPEG with the cell, as the ingest route already accepts. Super VL describes the frames that arrive. Squares without a frame stay without a picture.
- **More of the acoustic array.** The Pi recorder already accepts the channel count ALSA reports. The laptop classifier runs on the posted window. The four-channel bandpass and GCC-PHAT path is there for a multichannel block when the array survey is added. A bearing still needs that survey. The class labels do not.
- **A larger table.** Cell order lives in the sand-table geometry file and in the Uno snake. Add squares there. The heatmap still waits until the route is finished.
- **Another range sensor.** Post it on `POST /api/pi/ingest` beside radar and ultrasonic. It becomes evidence. It does not become a drive command.
- **A different operator radio.** The phone page is a browser on the same network. The command queue does not care which browser sent `F`, `B`, `L`, `R`, or `S`.

## Submission

Submit at [nebiusglobalaihackathon.devpost.com](https://nebiusglobalaihackathon.devpost.com/). The deadline is **Friday, October 30, 2026, 10:00 AM Pacific**. After that, the form, the video, and this repository should stay as submitted.

Use this as the project text:

> RubbleEcho is a physical sand-table rover for a search-and-rescue research setup. An operator drives it from a phone. A Raspberry Pi reads an ultrasonic ranger, a 60 GHz radar, and the acoustic array, and it posts a camera frame when one is available. An Arduino Uno drives the wheels through an L298N. The laptop classifies each gathered audio window as a knock, a scratch, or ambient sound. After nine squares, the laptop calls Nebius Token Factory. NVIDIA Nemotron 3 Nano writes the cell review from those readings, and Nemotron 3.5 Super VL describes a camera frame when one was posted. The models cannot move the rover. The heatmap appears only after that review.

Feedback worth sending with the form:

- Token Factory's OpenAI-compatible chat endpoint was enough. No extra SDK was required.
- Nano is the right size for a JSON review of nine short sensor cells. Super VL is reserved for a posted JPEG so the text call stays fast.
- The validator rejects motor, pin, and voltage fields, so a model reply cannot become a drive command.
- A missing or slow catalog check should leave the dashboard usable. This project does that: the rover path does not wait on the model.

Still required on the form:

- A public YouTube video under three minutes, with at least one minute of the rover moving, plus a short look at the dashboard after the model review.
- The same teammates, invited on the form, each of whom has accepted. Their names and majors are in the Team section above.
- The public GitHub URL of this repository.
