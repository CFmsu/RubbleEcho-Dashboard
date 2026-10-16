# Physical prototype

This path is added beside the existing simulation. The live-run page stays a labeled demo. Field mode stores photographs, Nebius responses, and serial events separately.

## What is connected

| Input | State |
| --- | --- |
| iPhone photograph (JPEG, PNG, HEIC) | Upload, 4×4 grid A1–D4, manual labels |
| Nebius vision model | Called only when `NEBIUS_API_KEY` is set and the catalog lists an image-capable model |
| Optional text model | Sector recommendations from the visual findings. The photograph is attached only when the selected catalog entry lists image input |
| ESP32-WROOM-32 BOOT button | Firmware in `firmware/esp32-boot-button`. Backend shows events only while the COM port stays open |
| HC-SR04 on Arduino UNO | Live run card. Sentence distances such as `65.84 cm` at 115200 baud |
| Uno eight-sensor bench | Bench test page. Sketch `firmware/uno-multisensor`. PIR and compass stay null until verified |

Piezo, mmWave radar, thermal camera, and a microphone array are not connected. A photograph cannot show a person under opaque debris. The HC-SR04 measures distance to an exposed surface.

## Windows setup

From the repository root, in PowerShell.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8080
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173` and choose **Field**.

Copy `.env.example` to `.env` before starting the backend if you want live inference. Leave `NEBIUS_API_KEY` empty to use manual labels only. The backend reads `.env` from the repository root. Do not commit `.env`.

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

## ESP32 BOOT button

1. Install the ESP32 board package in the Arduino IDE.
2. Open `firmware/esp32-boot-button/esp32-boot-button.ino`.
3. Select the ESP32-WROOM-32 board. The onboard BOOT button on the common DevKit is GPIO0, active low. Confirm that against your board silkscreen.
4. Upload. Then close the Arduino Serial Monitor so it releases the COM port.
5. On the Field page, choose that COM port and press Connect.
6. Press BOOT after the sketch has started. One JSON line arrives per press: `device_id`, `event_id`, `event_type`, `sequence`, `uptime_ms`.
7. Unplug the board or press Disconnect. The page must show DISCONNECTED and must not add events.

These events are labeled `MANUAL_HARDWARE_TEST`.

## Live HC-SR04 readings

The Live run page reads the sketch already running on the Uno. It accepts `Distance: 25 cm` and sentences such as `The nearest detected object is 65.84 cm away.` Baud on that board is **115200**. JSON lines that start with `{` are not treated as those sentences.

Close the Serial Monitor before pressing Connect. Windows only lets one program open the COM port.

The graph plots the centimeters the Arduino printed. A closer object is a smaller number. If the board is unplugged, the card says DISCONNECTED and does not add readings. Simulated mission cards stay labeled DEMO MODE and are not used as distance readings.

## Multi-sensor bench

Sensor lab is the existing test section. Its **Multi-sensor Bench Test** button and the **Bench test** nav item open the live eight-sensor page. The sketch is `firmware/uno-multisensor/Rubble_Echo_MB1010.ino`. It prints one JSON object about every 100 ms with `ms`, `flex_raw`, `light_pocket_raw`, `light_reference_raw`, `thermistor_raw`, `pir_left`, `pir_right`, `pir_ready`, `heading_deg`, `range_pw_us`, `range_cm`, and `range_status`.

`USE_PIR` and `USE_HMC6352` stay false until those modules are verified, so those fields are JSON null. Null is stored as an empty channel, not as zero. Analog channels stay ADC counts. `range_cm` is coarse clearance from the MB1010, using pulse microseconds / 147 × 2.54, and is null when the pulse is stale or at the far limit. Uploading this sketch replaces the sentence-format ultrasonic sketch on the same Uno.

## Nebius

`GET /api/inference/models` lists the account catalog and marks which ids accept images. Photograph analysis uses the first image-capable model unless `NEBIUS_VISION_MODEL` is set. Recommendations use the first NVIDIA text model unless `NEBIUS_REASONING_MODEL` is set. A text model is not sent an image unless its catalog record lists image input.

If the key is missing or the response fails schema checks, the Field page shows the error and keeps the photograph and any manual labels.

## Acceptance tests still requiring a person, a phone, a board, or a key

Automated tests cover upload, grid mapping, schema rejection, serial parsing, deduplication, disconnect, and demo/real separation. They do not plug in a board or call Nebius.

1. Upload a real iPhone photo and confirm the grid sits on the photograph.
2. Run vision analysis and confirm the model id shown is the one Nebius returned.
3. Run recommendations and confirm they cite the visual findings.
4. Press BOOT on a connected ESP32 and confirm one new manual-test event.
5. Unplug it and confirm DISCONNECTED with no new events.
6. Confirm the Live run card shows the centimeter sentence from the connected Uno at 115200 baud.
7. Upload the bench sketch only after that check. Confirm ADC counts, null PIR and heading, and MB1010 clearance on Bench test. Disconnect and confirm no new frames.
