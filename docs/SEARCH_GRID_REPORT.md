# Search grid report

Date: 2026-10-24

## What changed

The sand table is still the six measured cells: `A_NEAR`, `A_FAR`, `B_NEAR`, `B_FAR`, `C_NEAR`, `C_FAR`. **Plan grid** builds a virtual boundary on the traversable inset (10 cm inside the inner rim) and an order that covers every cell. **Guard obstacle** reads the latest ultrasonic sample. Inside 20 cm, or a missing echo, the next open cell is marked blocked and the planned look steps forward, then left, then right. **Read signals** paints a heatmap when the latest sample is a knock, a scratch, a periodic tap, or radar presence, then asks the reviewer where to listen next.

The radar card no longer draws a sweeping beam or a bearing blip. The MR60BHA2 reports range, presence, breath, heart rate, and target count. The mark on the bar is distance along that beam.

## What the model is allowed to do

Two calls, both advisory:

1. **Photo plan.** `plan_live` sends a camera note and the six point ids. The model may return `boundary`, `path`, and `look` (`forward`, `left`, or `right`). A path that names an unknown point, or any speed, voltage, PWM, or pin, is rejected and the local order is kept. A boundary outside the 105 by 80 cm table is discarded and the traversable inset stays the virtual line. The model's point order and look are kept when those two checks pass.
2. **After the sensors.** The existing reason call now also receives the remaining path and the blocked cells. It may recommend `settle_and_listen`, `rescan_at_point`, `capture`, `stop`, or `needs_operator`. `rescan_at_point` is only meaningful for a point still on the path. It still requires approval.

Until `NEBIUS_API_KEY`, `NEBIUS_MODEL_ID`, and `AI_ENABLED` are set, both steps use the local grid and the local evidence readout. No Token Factory call is made. On this machine the plan call did run. The first reply had no JSON. The next reply had a boundary outside the table, so the inset remained and the six-cell order stayed local. The following click keeps a valid model path and look, and still replaces an out-of-table boundary with the inset.

## What this program does not do

- It does not command the L298N, the Cytron driver, the HC-06, or any pin. `execute_hardware` stays false. The ultrasonic field `commanded_pin` stays null.
- `look` is the planned facing for the camera and the ultrasonic. Nothing rotates a servo.
- A heatmap uses the camera pose only when that pose is already valid. Otherwise it uses the current grid cell. There is no stored photo yet: the camera slot does not keep a frame, so the plan says the frame was not stored.
- A close obstacle updates the grid. It does not drive around the obstacle.

## Contracts that moved

| Before | After |
| --- | --- |
| The model returned a recommendation and was not given a path | The model may return a grid path and a virtual boundary, and the reason call can see that path |
| The radar card animated a beam from −80° to 80° and plotted `display_bearing_deg` | The card shows range only |
| The map always drew a dashed route through the six points and slid a rover along it during a simulation run | A search plan draws the amber boundary and the remaining teal order. The simulation marker stays available only when no plan is set |
| A failed live reason call still holds motion | A failed live **plan** call does not latch ESTOP. It keeps the local grid and records `model_error` |
