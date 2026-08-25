import asyncio
import json
import os
import time
from collections import deque

import numpy as np
from vosk import Model, KaldiRecognizer

from config_loader import BASE_DIR, CFG
from mic_stream import AsyncMicStream

_models = {}

_hindi_to_roman_map = {
    "ओपन": "open", "खोलो": "open", "खोल": "open",
    "बंद": "close", "बंद करो": "close", "बंद कर": "close",
    "मिनिमाइज": "minimize", "घटाओ": "reduce", "बढ़ाओ": "increase",
    "विंडो": "window", "स्क्रीन": "screen", "फ़ाइल": "file",
    "फ़ोल्डर": "folder", "डिलीट": "delete", "स्क्रीनशॉट": "screenshot",
    "क्लिक": "click", "टाइप": "type", "कॉपी": "copy", "पेस्ट": "paste",
    "वॉल्यूम": "volume", "ब्राइटनेस": "brightness", "कंप्यूटर": "computer",
    "पीसी": "pc", "नोटपैड": "notepad", "कलकुलेटर": "calculator",
    "ब्राउज़र": "browser", "गूगल क्रोम": "chrome", "यूट्यूब": "youtube",
    "करो": "do", "करना": "do", "जा": "go", "जा दो": "go",
}


def _normalize_hindi(text: str) -> str:
    if not text:
        return text
    t = text.lower().strip()
    words = t.split()
    roman = [_hindi_to_roman_map.get(w, w) for w in words]
    result = " ".join(roman)
    phrase_map = {
        "ओपन यूट्यूब": "open youtube", "बंद करो यूट्यूब": "close youtube",
        "स्क्रीनशॉट लो": "screenshot", "वॉल्यूम बढ़ाओ": "volume up",
        "वॉल्यूम घटाओ": "volume down", "ब्राइटनेस बढ़ाओ": "brightness up",
        "ब्राइटनेस घटाओ": "brightness down", "माउस क्लिक": "mouse click",
        "डबल क्लिक": "double click", "राईट क्लिक": "right click",
    }
    for hin, rom in phrase_map.items():
        if hin in result.lower():
            result = result.lower().replace(hin, rom)
    return result


def _get_model(lang="hi"):
    global _models
    if lang in _models:
        return _models[lang]
    paths = {"hi": "models/vosk-hindi-small", "en": "models/vosk-english-small"}
    rel = paths.get(lang) or CFG.get("vosk_model_path", "models/vosk-hindi-small")
    path = os.path.join(BASE_DIR, rel)
    if not os.path.isdir(path):
        raise FileNotFoundError(f"Vosk model not found: {path}")
    m = Model(path)
    _models[lang] = m
    return m


class SileroVAD:
    """Silero VAD wrapper using ONNX Runtime.

    Supports both the standard Silero VAD interface (single `state` input)
    and the legacy interface shipped with openwakeword (`h`/`c` inputs).
    """

    def __init__(self, model_path=None, threshold=0.5):
        if model_path is None:
            # Reuse the Silero VAD model shipped with openwakeword
            model_path = os.path.join(BASE_DIR, "models", "openwakeword", "silero_vad.onnx")
        if not os.path.isabs(model_path):
            model_path = os.path.join(BASE_DIR, model_path)
        import onnxruntime as ort
        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self.threshold = threshold
        self._sr = 16000
        self._window_size = 512  # 32ms at 16kHz

        # Detect model interface
        input_names = [i.name for i in self.session.get_inputs()]
        self._legacy = "h" in input_names and "c" in input_names
        # Detect LSTM state dimension from the model
        if self._legacy:
            state_shape = next(i.shape for i in self.session.get_inputs() if i.name == "h")
        else:
            state_shape = next(i.shape for i in self.session.get_inputs() if i.name == "state")
        state_dim = int(state_shape[2])  # hidden size
        self._h = np.zeros((2, 1, state_dim), dtype=np.float32)
        self._c = np.zeros((2, 1, state_dim), dtype=np.float32)
        self._state = np.zeros((2, 1, state_dim), dtype=np.float32)
        self._context = deque(maxlen=8)  # ~256ms context

    def reset(self):
        d = self._h.shape[2]
        self._h = np.zeros((2, 1, d), dtype=np.float32)
        self._c = np.zeros((2, 1, d), dtype=np.float32)
        self._state = np.zeros((2, 1, d), dtype=np.float32)
        self._context.clear()

    def __call__(self, audio_chunk: bytes) -> float:
        """Return speech probability for 16kHz int16 audio chunk."""
        # Convert to float32 mono
        audio = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
        # Process in 512-sample windows
        probs = []
        for i in range(0, len(audio), 512):
            chunk = audio[i:i+512]
            if len(chunk) < 512:
                chunk = np.pad(chunk, (0, 512 - len(chunk)))
            inp = chunk.reshape(1, 512).astype(np.float32)
            # Run inference
            if self._legacy:
                ort_inputs = {
                    "input": inp,
                    "h": self._h,
                    "c": self._c,
                    "sr": np.array([self._sr], dtype=np.int64),
                }
                ort_outs = self.session.run(None, ort_inputs)
                speech_prob = float(ort_outs[0][0][0])
                self._h = ort_outs[1]
                self._c = ort_outs[2]
            else:
                ort_inputs = {
                    "input": inp,
                    "state": self._state,
                    "sr": np.array([self._sr], dtype=np.int64),
                }
                ort_outs = self.session.run(None, ort_inputs)
                speech_prob = float(ort_outs[0][0][0])
                self._state = ort_outs[1]
            probs.append(speech_prob)
        return max(probs) if probs else 0.0


class StreamingSTT:
    """Streaming STT with Vosk + Silero VAD for turn detection."""

    def __init__(self, lang="hi", silence_threshold=0.5, pause_sec=1.5, normalize=True):
        self.lang = lang
        self.silence_threshold = silence_threshold
        self.pause_sec = pause_sec
        self.normalize = normalize
        self.model = _get_model(lang)
        self.rec = KaldiRecognizer(self.model, 16000)
        self.rec.SetWords(False)
        self.vad = SileroVAD()
        self._buffer = bytearray()
        self._last_speech_time = None
        self._utterance_started = False

    def reset(self):
        self.rec = KaldiRecognizer(self.model, 16000)
        self.rec.SetWords(False)
        self.vad.reset()
        self._buffer.clear()
        self._last_speech_time = None
        self._utterance_started = False

    def process_chunk(self, audio_chunk: bytes) -> tuple[str | None, str | None]:
        """
        Process audio chunk. Returns (partial_text, final_text).
        final_text is set when utterance ends (silence detected).
        """
        # VAD
        speech_prob = self.vad(audio_chunk)
        is_speech = speech_prob > 0.5

        # Feed to Vosk
        self.rec.AcceptWaveform(audio_chunk)
        partial = json.loads(self.rec.PartialResult()).get("partial", "")

        now = time.time()
        final_text = None

        if is_speech:
            if not self._utterance_started:
                self._utterance_started = True
            self._last_speech_time = time.time()

        # Check for end of utterance (silence pause)
        if self._utterance_started and self._last_speech_time:
            if time.time() - self._last_speech_time > self.pause_sec:
                # Utterance ended
                final_result = json.loads(self.rec.FinalResult())
                final_text = final_result.get("text", "").strip()
                if final_text and self.normalize:
                    final_text = _normalize_hindi(final_text)
                # Reset for next utterance
                self.rec = KaldiRecognizer(_get_model(self.lang), 16000)
                self.rec.SetWords(False)
                self.vad.reset()
                self._utterance_started = False
                self._last_speech_time = None

        return partial if partial else None, final_text


import numpy as np


def resample_audio(chunk: bytes, from_sr: int, to_sr: int) -> bytes:
    """Resample int16 audio from from_sr to to_sr."""
    if from_sr == to_sr:
        return chunk
    data = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
    n = len(data)
    if n == 0:
        return chunk
    x_old = np.linspace(0, 1, n, endpoint=False)
    x_new = np.linspace(0, 1, int(n * to_sr / from_sr), endpoint=False)
    resampled = np.interp(x_new, x_old, data).astype(np.int16)
    return resampled.tobytes()


async def stt_stream(mic: 'AsyncMicStream', lang="hi", pause_sec=1.5, normalize=True):
    """Async generator yielding (partial_text, final_text) from microphone."""
    import numpy as np

    stt = StreamingSTT(lang=lang, pause_sec=pause_sec, normalize=normalize)
    mic_sr = getattr(mic, "samplerate", 16000)

    def _resample(chunk: bytes) -> bytes:
        if mic_sr == 16000:
            return chunk
        data = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
        n = len(data)
        if n == 0:
            return chunk
        x_old = np.linspace(0, 1, n, endpoint=False)
        x_new = np.linspace(0, 1, int(n * 16000 / mic_sr), endpoint=False)
        resampled = np.interp(x_new, x_old, data).astype(np.int16)
        return resampled.tobytes()

    while True:
        chunk = await mic.read_audio()
        if mic_sr != 16000:
            chunk = _resample(chunk)
        partial, final = stt.process_chunk(chunk)
        if partial or final:
            yield partial, final


def _detect_lang(text: str) -> str:
    t = text.lower()
    hindi_words = ["kya", "hai", "ho", "mein", "tum", "aap", "bolo", "batao", "karo",
                   "kaise", "acha", "theek", "nahi", "haan", "mera", "kaun", "abhi",
                   "kal", "aaj", "parso", "kitna", "kitne", "kholo", "chalao"]
    if any(w in t.split() for w in hindi_words):
        return "hi"
    ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
    total_letters = sum(1 for c in text if c.isalpha())
    if total_letters > 0 and ascii_letters / total_letters > 0.95:
        return "en"
    return "hi"


if __name__ == "__main__":
    import sys
    sys.path.insert(0, r".")
    from mic_stream import AsyncMicStream

    async def test():
        async with AsyncMicStream() as mic:
            print("Listening... (Ctrl+C to stop)")
            async for partial, final in stt_stream(mic, lang="hi", pause_sec=1.5):
                if partial:
                    print(f"  [partial] {partial}", end="\r")
                if final:
                    lang = _detect_lang(final)
                    print(f"\n[Final] {final} (lang={lang})")

    asyncio.run(test())