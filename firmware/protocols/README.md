# Rover command frame

The Pi sends one JSON object, a pipe, and a CRC32 of the JSON bytes, then a newline.

```
{"command_id":"c1","ttl_ms":500,"type":"stop"}|a1b2c3d4
```

The CRC is `zlib.crc32` over the exact JSON bytes, printed as 8 lowercase hex digits. The Python reference is `backend/app/drivers/encoders.py`.

Allowed `type` values are `stop`, `move_cm`, `turn_deg`, `rescan`, `capture`, and `knock_test_request`. Any other type is rejected. A repeated `command_id` is a fault.

Sensor lines from a microcontroller use a prefix so a status message cannot be read as a detection:

- `RADAR {json}`
- `ULTRASONIC {json}`
- `PIEZO {json}`
- `ENC {json}`
- `ACK {json}`

A line without a prefix is ignored. The radar JSON may include only the fields parsed in `backend/app/drivers/radar_mr60bha2.py`. Unknown keys, including invented micro-motion fields, are rejected.

Pin numbers, baud rate, and motor grouping are `NEEDS_HARDWARE_VERIFICATION`. The sketches in this folder refuse to drive outputs until a local, untracked pin header is supplied and `PINS_VERIFIED` is set to 1.
