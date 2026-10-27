from app.services.briefing import _pdf, _png_rgb, briefing_pdf, narrate
from app.services.sim_media import sample_png


def test_narration_is_spoken_and_names_the_first_stop() -> None:
    text = narrate(
        [
            {
                "point_id": "A_NEAR",
                "score": 0.7,
                "readings": {"sound": "knock", "radar_presence": True, "distance_m": 0.4},
            },
            {
                "point_id": "A_FAR",
                "score": 0.2,
                "readings": {"sound": "ambient", "radar_presence": False},
            },
        ],
        "A_NEAR",
    )
    assert "Walk to A_NEAR first" in text
    assert "sharp knock" in text
    assert "camera frame" in text
    assert "dBFS" not in text
    assert "adc" not in text.lower()


def test_pdf_embeds_the_camera_frame() -> None:
    image = _png_rgb(sample_png("A_NEAR", (40, 90, 160)))
    assert image is not None
    width, height, rgb = image
    assert width == 320 and height == 180
    assert len(rgb) == width * height * 3
    pdf = _pdf(
        "RubbleEcho briefing",
        "Walk to A_NEAR first. We heard a sharp knock.",
        "Read this aloud at the table.",
        image,
    )
    assert pdf.startswith(b"%PDF")
    assert b"/Subtype /Image" in pdf
    assert b"Walk to A_NEAR" in pdf


def test_a_wrong_next_stop_is_replaced_with_the_ranked_one() -> None:
    from app.services.briefing import align_narrative

    text = align_narrative(
        "Knock was heard at A_NEAR. A pulse was detected there and the image is the camera frame from that stop. Next the search should go to B_NEAR.",
        [
            {"point_id": "A_NEAR", "score": 0.7, "readings": {"sound": "knock", "radar_presence": True}},
            {"point_id": "A_FAR", "score": 0.4, "readings": {"sound": "knock", "radar_presence": False}},
            {"point_id": "B_NEAR", "score": 0.1, "readings": {"sound": "ambient", "radar_presence": False}},
        ],
        "A_NEAR",
    )
    assert "A_NEAR" in text
    assert "camera frame" in text
    assert "After that, look at A_FAR." in text
    assert "B_NEAR" not in text


def test_briefing_keeps_a_written_narrative() -> None:
    class State:
        reasoning = {
            "narrative": "Walk to B_NEAR first. That is the square that stood out on this pass.",
            "recommendation": {"point_id": "B_NEAR"},
        }
        heatmap: list = []
        media_camera = None
        trial_id = "trial-1"

    pdf = briefing_pdf(State())
    assert pdf.startswith(b"%PDF")
    assert b"Walk to B_NEAR" in pdf
