import io
import numpy as np
import pytest
import soundfile as sf
from x4_companion.audio import AudioRecorder

class _FakeStream:
    def __init__(self, samplerate, channels, dtype, device, callback):
        self.callback = callback
    def start(self):
        chunk = np.zeros((8000, 1), dtype=np.int16)
        chunk[::100] = 1000
        self.callback(chunk, len(chunk), None, None)
    def stop(self): pass
    def close(self): pass

def test_recorder_returns_valid_wav(monkeypatch):
    rec = AudioRecorder(sample_rate=16000)
    monkeypatch.setattr(rec._sd, "InputStream", _FakeStream)
    rec.start()
    wav = rec.stop()
    assert wav.startswith(b"RIFF")
    audio, sr = sf.read(io.BytesIO(wav))
    assert sr == 16000
    assert len(audio) == 8000

def test_recorder_returns_empty_when_no_audio(monkeypatch):
    class _NoCallbackStream(_FakeStream):
        def start(self): pass
    rec = AudioRecorder(sample_rate=16000)
    monkeypatch.setattr(rec._sd, "InputStream", _NoCallbackStream)
    rec.start()
    assert rec.stop() == b""
