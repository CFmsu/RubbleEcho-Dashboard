# Hardware wiring prerequisites

Nothing in this list was verified on a bench during the software change. Do not energize the 12 V circuit until each applicable row is checked by a person.

| Item | Status |
| --- | --- |
| Solenoid flyback diode across the coil | Not confirmed in inventory |
| Fuse on the 12 V branch | Planned, not confirmed owned |
| Emergency stop that cuts motor and solenoid power | Planned, not confirmed owned |
| MOSFET gate resistor and gate pulldown | Not confirmed |
| Piezo series resistor, bias, and clamp before any 3.3 V ADC | Required before connection |
| HC-SR04 ECHO level shift if the receiver pin is not 5 V tolerant | Required before connection to a Pi or ESP32 |
| Common ground between logic and power return | Not inspected |
| MDD10A current versus the actual motor count and stall current | Motor count unknown |
| Rover footprint and stop distance | Unmeasured |
| Camera models, CSI versus USB, and whether any lens is panoramic | Not enumerated |
| ReSpeaker firmware mode, 2-channel processed versus raw 6-channel | Not enumerated |
| MR60BHA2 firmware revision | Not read from a device |
| Bluetooth module type | Likely HC-05, not verified |
| Arduino Mega model | Not verified |
| Reference piezo on the brick inside box A | Not in the stated inventory |

The one piezo disk is assigned in software as a stationary surface contact receiver. It is not treated as the buried reference sensor.

Software pulse limit is 40 ms. The 250 ms figure is the onset spacing, not a hold time. The solenoid output flag stays false in this build.
