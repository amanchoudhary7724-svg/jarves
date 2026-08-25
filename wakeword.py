import os
import queue
import sys
import time

import numpy as np
from openwakeword.model import Model

from config_loader import CFG
from mic_stream import MicStream


class WakeWordDetector:
    def __init__(self):
        self.threshold = CFG.get("wake_word_threshold", 0.6)
        self.model = None
        self._model_name = "hey_jarvis"

    def _load_model(self):
        if self.model is None:
            print("[WakeWord] Model load ho raha hai...")
            self.model = Model(
                wakeword_models=[self._model_name],
                inference_framework="onnx",
            )
            print(f"[WakeWord] Ready! '{self._model_name}' sun raha hoon...")

    def listen(self, timeout_s=300.0, callback=None):
        self._load_model()
        mic = MicStream(blocksize=1280, samplerate=16000)
        start = time.time()
        try:
            mic.start()
            while time.time() - start < timeout_s:
                audio = np.frombuffer(mic.read(), dtype=np.int16)
                scores = self.model.predict(audio)
                score = scores.get(self._model_name, 0)
                if score > self.threshold:
                    print(f"\n[WakeWord] Detect hua! (score={score:.2f})")
                    return True
        finally:
            try:
                mic.stop()
                mic.close()
            except Exception:
                pass
        return False


if __name__ == "__main__":
    print("WakeWord test mode - 'hey jarvis' boliye (30 sec timeout)...")
    wd = WakeWordDetector()
    found = wd.listen(timeout_s=30)
    print("Detected!" if found else "Kuch nahi suna.")
