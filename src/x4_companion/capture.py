import io
from abc import ABC, abstractmethod
from PIL import Image

class Capture(ABC):
    @abstractmethod
    def get_current_frame(self) -> bytes:
        """Return PNG-encoded bytes of the current screen."""

class DxcamCapture(Capture):
    def __init__(self, max_width: int = 896, jpeg_quality: int = 80):
        import dxcam
        self._camera = dxcam.create()
        self._max_width = max_width
        self._jpeg_quality = jpeg_quality

    def get_current_frame(self) -> bytes:
        frame = self._camera.grab()
        if frame is None:
            raise RuntimeError("capture failed (try borderless windowed mode in X4)")
        img = Image.fromarray(frame[:, :, ::-1])
        if img.width > self._max_width:
            ratio = self._max_width / img.width
            img = img.resize((self._max_width, int(img.height * ratio)))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=self._jpeg_quality, optimize=True)
        return buf.getvalue()

class FakeCapture(Capture):
    def __init__(self, png_bytes: bytes):
        self._png = png_bytes
    def get_current_frame(self) -> bytes:
        return self._png
