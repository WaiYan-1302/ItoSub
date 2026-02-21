from unittest.mock import MagicMock
from itosub.asr.faster_whisper_file import FasterWhisperFileTranscriber

def test_transcribe_file_wraps_segments(monkeypatch):
    fake_model = MagicMock()

    # Fake segment objects
    seg1 = MagicMock(start=0.0, end=1.2, text="Hello")
    seg2 = MagicMock(start=1.2, end=2.5, text="world.")
    fake_model.transcribe.return_value = ([seg1, seg2], MagicMock())

    tr = FasterWhisperFileTranscriber(model_size="base")

    # Replace _get_model to avoid loading real model
    monkeypatch.setattr(tr, "_get_model", lambda: fake_model)

    out = tr.transcribe_file("dummy.wav")
    assert len(out) == 2
    assert out[0].text == "Hello"
    assert out[1].text == "world."
    assert out[1].t1 == 2.5