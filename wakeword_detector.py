import os
import numpy as np
from pathlib import Path

try:
    from openwakeword.model import Model as OWWModel
    OWW_AVAILABLE = True
except Exception:
    OWW_AVAILABLE = False

BASE_DIR = Path(__file__).resolve().parent


class WakeWordDetector:
    """Wake word detector using openwakeword models."""

    def __init__(self, model_name="hey_jarvis", threshold=0.5):
        self.model_name = model_name
        self.threshold = threshold
        self._model = None
        self._sample_rate = 16000

    def load(self):
        """Load the openwakeword model."""
        if not OWW_AVAILABLE:
            return False
        model_dir = BASE_DIR / "models" / "openwakeword"
        model_path = model_dir / f"{self.model_name}_v0.1.onnx"
        embedding_path = model_dir / "embedding_model.onnx"
        melspec_path = model_dir / "melspectrogram.onnx"
        if not (model_path.exists() and embedding_path.exists() and melspec_path.exists()):
            return False
        try:
            self._model = OWWModel(
                wakeword_models=[str(model_path)],
                inference_framework="onnx",
                melspec_model_path=str(melspec_path),
                embedding_model_path=str(embedding_path),
            )
            return True
        except Exception:
            return False

    def predict(self, audio_chunk: bytes) -> float:
        """Return detection score for 16kHz int16 audio chunk."""
        if self._model is None:
            return 0.0
        # openwakeword expects RAW INT16 numpy arrays of 1280 samples
        # (80ms at 16kHz). Feeding float32 normalized audio silently
        # produces 0.0 scores.
        import numpy as np
        audio = np.frombuffer(audio_chunk, dtype=np.int16)
        if len(audio) < 1280:
            audio = np.pad(audio, (0, 1280 - len(audio)))
        elif len(audio) > 1280:
            audio = audio[:1280]
        prediction = self._model.predict(audio)
        # prediction is a dict keyed by model FILENAME (e.g. 'hey_jarvis_v0.1'),
        # not our friendly name - take the max score across all models.
        if not prediction:
            return 0.0
        return float(max(prediction.values()))

    def detect(self, audio_chunk: bytes) -> bool:
        """Return True if wake word detected."""
        score = self.predict(audio_chunk)
        return score >= self.threshold

    def reset(self):
        if self._model:
            self._model.reset()


class UnavailableWakeWordDetector:
    """Safe fallback when a wake-word model is unavailable.

    It never activates the assistant; callers must provide an explicit
    alternative input path rather than silently accepting all audio.
    """

    def load(self):
        return True

    def predict(self, audio_chunk: bytes) -> float:
        return 0.0

    def detect(self, audio_chunk: bytes) -> bool:
        return False

    def reset(self):
        pass


def create_wake_word_detector(model_name="hey_jarvis", threshold=0.5):
    """Factory: returns real detector if available, else a safe inactive detector."""
    det = WakeWordDetector(model_name, threshold)
    if det.load():
        return det
    return UnavailableWakeWordDetector()


if __name__ == "__main__":
    import soundfile as sf
    det = create_wake_word_detector()
    print("WakeWordDetector loaded:", type(det).__name__)
    # Test with silence
    print("Silence score:", det.predict(b"\x00" * 2560))
