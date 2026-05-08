import io

import numpy as np
import soundfile as sf


class AudioRecorder:
    def __init__(self, sample_rate: int = 16000, device: str | int | None = None):
        import sounddevice as sd
        self._sd = sd
        self._sample_rate = sample_rate
        self._device = device or None
        self._stream = None
        self._chunks: list[np.ndarray] = []

    def start(self) -> None:
        self._chunks = []

        def callback(indata, frames, time, status):
            self._chunks.append(indata.copy())

        self._stream = self._sd.InputStream(
            samplerate=self._sample_rate,
            channels=1,
            dtype="int16",
            device=self._device,
            callback=callback,
        )
        self._stream.start()

    def stop(self) -> bytes:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._chunks:
            return b""
        audio = np.concatenate(self._chunks, axis=0)
        buf = io.BytesIO()
        sf.write(buf, audio, self._sample_rate, format="WAV", subtype="PCM_16")
        return buf.getvalue()


class AudioPlayer:
    def __init__(self, sample_rate: int = 24000, device: str | int | None = None):
        import sounddevice as sd
        self._sd = sd
        self._sample_rate = sample_rate
        self._device = device or None

    def open_stream(self) -> "StreamingPlayback":
        return StreamingPlayback(self._sd, self._sample_rate, self._device or None)


class StreamingPlayback:
    """Write linear16 PCM bytes as they arrive; audio plays as soon as the
    output buffer has enough samples."""

    def __init__(self, sd, sample_rate: int, device):
        self._sd = sd
        self._stream = sd.RawOutputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            device=device,
        )
        self._stream.start()

    def write(self, pcm_bytes: bytes) -> None:
        if not pcm_bytes or pcm_bytes == b"PCM_FAKE":
            return
        self._stream.write(pcm_bytes)

    def close(self) -> None:
        try:
            self._stream.stop()
        finally:
            self._stream.close()
