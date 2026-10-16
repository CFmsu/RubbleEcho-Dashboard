/** Guided-demo script for team walkthroughs. Keys change when the story beat changes. */

export type NarrationBeat = {
  key: string;
  title: string;
  body: string;
};

export function demoNarrationBeat(input: {
  demo: boolean;
  status: string;
  phase: string;
  probeCount: number;
  outcome: string | null;
  scenarioLabel: string;
  confidence: number;
  x: number;
  y: number;
}): NarrationBeat | null {
  if (!input.demo) {
    if (input.status === "IDLE") {
      return {
        key: "idle",
        title: "Team walkthrough",
        body: "Press Play demo. We will walk a Structural Collapse scene: knock, listen, update the map, and mark a candidate spot for rescue verification.",
      };
    }
    return null;
  }

  const pct = Math.round(input.confidence * 100);
  const beforeCapture =
    input.phase === "NAVIGATING" ||
    input.phase === "SELECTING_TARGET" ||
    input.phase === "CONTACT" ||
    input.phase === "KNOCKING" ||
    input.phase === "IDLE";
  const knock = Math.min(5, Math.max(1, beforeCapture ? input.probeCount + 1 : Math.max(1, input.probeCount)));
  const probeClamped = knock;

  if (input.status === "COMPLETE" || input.outcome === "SURVIVOR LOCATION IDENTIFIED" || input.phase === "LOCATION_IDENTIFIED") {
    return {
      key: "done",
      title: "Demo result",
      body: `Candidate spot marked near X ${input.x.toFixed(1)}, Y ${input.y.toFixed(1)} with about ${pct}% estimated confidence. This is still a simulation — a rescue team must verify before any real action.`,
    };
  }

  if (input.phase === "HUMAN_RESPONSE_DETECTED" || input.phase === "CONFIRMING") {
    return {
      key: "confirm",
      title: "Strong reply",
      body: "The last knock got a clear answer. Sensors agree: sound, vibration, and a hollow-space hint. We treat this as a candidate location, not a rescue.",
    };
  }

  if (input.phase === "IDLE" && input.status === "ACTIVE") {
    return {
      key: "boot",
      title: "Starting demo",
      body: `Example scenario: ${input.scenarioLabel}. A survivor source is hidden from the search algorithm. The robot will probe five spots along a smart path.`,
    };
  }

  const place = `Knock ${probeClamped} of 5`;

  if (input.phase === "NAVIGATING" || input.phase === "SELECTING_TARGET") {
    const lines: Record<number, string> = {
      1: "First stop — quiet rubble near the entry. We expect little or no reply here. Watch the robot drive, then knock.",
      2: "Moving deeper. Still exploring. The map should stay mostly cool unless something answers.",
      3: "Heading toward a more interesting zone. If a weak reply appears, the belief map will start to warm.",
      4: "Following the rising signal. This is the adaptive idea: go where the evidence points, not every grid cell.",
      5: "Final approach to the hottest cell. If we get a confirmed reply, we mark a candidate for the team.",
    };
    return {
      key: `nav-${probeClamped}`,
      title: place,
      body: lines[probeClamped] ?? "Driving to the next probe point.",
    };
  }

  if (input.phase === "CONTACT") {
    return {
      key: `contact-${probeClamped}`,
      title: place,
      body: "Robot touches the rubble face and checks that the surface looks safe enough to knock.",
    };
  }

  if (input.phase === "KNOCKING") {
    return {
      key: `knock-${probeClamped}`,
      title: place,
      body: "Knock. A short strike goes into the structure so vibration and sound sensors can listen for a reply.",
    };
  }

  if (input.phase === "LISTENING") {
    const lines: Record<number, string> = {
      1: "Listening… Quiet. No human-like tap. That is useful: we learn where not to spend time.",
      2: "Listening… Background noise only. Not a clear reply yet.",
      3: "Listening… A weak answer may be coming through. Watch vibration and audio scores rise a little.",
      4: "Listening… Stronger taps. This looks like a possible response from deeper in the debris.",
      5: "Listening… Clear, repeated reply. This is the confirmation knock of the demo.",
    };
    return {
      key: `listen-${probeClamped}`,
      title: place,
      body: lines[probeClamped] ?? "Listening for a reply after the knock.",
    };
  }

  if (input.phase === "ANALYZING") {
    return {
      key: `analyze-${probeClamped}`,
      title: place,
      body: "Mixing the sensors: sound 35%, vibration 30%, hollow-space 20%, camera 15%. That combined score updates our confidence.",
    };
  }

  if (input.phase === "UPDATING_MAP") {
    const lines: Record<number, string> = {
      1: "Map update: this cell stays cool. Low score means low belief here.",
      2: "Map update: slight warmth from ambient noise — still not a target.",
      3: "Map update: warmer cells appear. Belief is shifting toward this neighborhood.",
      4: "Map update: hot streak forming. Smart path will prefer nearby high-belief spots.",
      5: "Map update: peak belief locked on this area. Ready to mark a candidate.",
    };
    return {
      key: `map-${probeClamped}`,
      title: place,
      body: lines[probeClamped] ?? "Updating the belief map from this knock.",
    };
  }

  return {
    key: `phase-${input.phase}-${probeClamped}`,
    title: place,
    body: "Demo in progress — follow the map and the sensor tiles as each knock lands.",
  };
}
