from pathlib import Path
from x4_companion.capture import FakeCapture

FIXTURE = Path(__file__).parent / "fixtures" / "x4_screenshot.png"

def test_fake_capture_returns_supplied_bytes():
    data = FIXTURE.read_bytes()
    cap = FakeCapture(data)
    assert cap.get_current_frame() == data
    assert cap.get_current_frame()[:8] == b"\x89PNG\r\n\x1a\n"
