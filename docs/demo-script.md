# Demo script

A three-minute briefing. Stay on the mission dashboard. Press `D` or **Start Demo**. Leave the speed at 1× if you want the full sequence, or 2× if the room is short on time. Press `P` for presentation mode.

Say clearly that the screen is in simulation mode.

## 0:00 — Problem

Disaster rubble is a large search area. Checking every point the same way spends time where there is no evidence.

## 0:30 — RubbleEcho concept

The robot does not only listen. It stops, knocks, and uses the vibration and sound that come back. Each probe updates a belief map. The next probe goes where that evidence is strongest.

Point to the header: **SIMULATION MODE**. The hardware row shows the AI engine as simulated.

## 1:00 — Start mission

Start the demo. The robot leaves the deployment point. The event log records mission start and the first probe.

## 1:20 — Knock / listen

When the phase line reaches KNOCK and LISTEN, point at the piezo chart and the audio chart. The first probes should read as no human response, then a weak vibration anomaly.

## 1:40 — Adaptive map

The map starts nearly uniform and then concentrates. Mention that the search algorithm never receives the hidden source. It only sees the features the sensors return.

## 2:00 — Human response

A later probe should show a possible tap. The decision engine states why the next point was chosen. The reasoning provider reads **SIMULATED**.

## 2:20 — Confirmation

The robot runs a confirmation probe. If the response repeats, the banner reads **Candidate survivor location identified** and **Awaiting rescue team verification**. Do not say the person has been rescued.

## 2:40 — Search comparison

Open the search-efficiency panel. Grid search and adaptive search are both labeled **simulated results**. They illustrate why adaptive probing can take fewer measurements in this model. They are not field performance.

## 3:00 — Conclusion

What exists today is the simulation, the dashboard, and the adapter seams. What is next is bench sensors, a striker, a chassis, then NVIDIA or Nebius behind the reasoning interface, then a controlled rubble test.

Keyboard reminders: Space pauses, `N` steps one phase, `R` resets, `P` toggles presentation, `D` starts the demo.
