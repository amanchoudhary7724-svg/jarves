import asyncio
import os
import tempfile
import subprocess

import soundfile as sf

from config_loader import CFG


def _detect_emotion_from_text(text: str) -> str:
    """Simple emotion detection from text."""
    text = text.lower()
    if any(w in text for w in ["khush", "accha", "badhiya", "great", "awesome", "badhiya", "mast"]):
        return "happy"
    if any(w in text for w in ["dukh", "bura", "sad", "gussa", "angry", "naraz"]):
        return "sad"
    if any(w in text for w in ["darr", "bhay", "fear", "scared", "dar"]):
        return "fear"
    if any(w in text for w in ["hairan", "shock", "surprise", "wow", "omg"]):
        return "surprise"
    return "neutral"


class StreamingTTS:
    """Streaming TTS using Piper (local, fast, supports Hindi+English)."""

    def __init__(self, lang="hi"):
        self.lang = lang
        self._voice_map = {
            "hi": "models/piper/hi_IN-pratham-medium.onnx",
            "en": "models/piper/en_US-lessac-medium.onnx",
        }
        self._voice_config_map = {
            "hi": "models/piper/hi_IN-pratham-medium.onnx.json",
            "en": "models/piper/en_US-lessac-medium.onnx.json",
        }
        self._proc = None
        self._sample_rate = 22050

    def _get_voice_path(self):
        return self._voice_map.get(self.lang, self._voice_map["hi"])

    def _get_config_path(self):
        return self._voice_config_map.get(self.lang, self._voice_config_map["hi"])

    async def synthesize_stream(self, text: str, lang=None):
        """
        Stream TTS audio chunks via Piper.
        Yields audio chunks (bytes, int16, 22050 Hz mono).
        """
        lang = lang or self.lang
        voice = self._voice_map.get(lang, self._voice_map["hi"])
        config = self._voice_config_map.get(lang, self._voice_config_map["hi"])

        if not text.strip():
            return

        # Write text to temp file for Piper
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(text)
            text_file = f.name

        try:
            # Piper CLI: piper --model <model> --config <config> --output_file <output> < text.txt
            # For streaming, we use piper with --output_raw to stdout
            cmd = [
                "piper",
                "--model", self._get_voice_path(),
                "--config", self._get_config_path(),
                "--output_raw",
                "--sentence_silence", "0.2",
            ]

            # Use stdin for text input, stdout for raw audio
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )

            # Write text to stdin
            _, _ = await proc.communicate(input=text.encode())

            # Read stdout in chunks
            # Piper outputs raw 16-bit PCM at 22050 Hz
            chunk_size = 4096  # ~93ms at 22050 Hz
            while True:
                chunk = await proc.stdout.read(4096)
                if not chunk:
                    break
                yield chunk

            await proc.wait()

        except Exception as e:
            # Fallback to pyttsx3 if Piper fails
            async for chunk in self._fallback_tts(text, lang):
                yield chunk

    async def _fallback_tts(self, text: str, lang: str):
        """Fallback to pyttsx3 (blocking, full utterance)."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 170)
            voices = engine.getProperty('voices')
            for v in voices:
                if lang == "hi" and "hindi" in v.name.lower():
                    engine.setProperty('voice', v.id)
                    break
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_file = f.name
            engine.save_to_file(text, wav_file)
            engine.runAndWait()
            # Read and yield in chunks
            data, sr = sf.read(wav_file, dtype="int16")
            if sr != 22050:
                import librosa
                data = librosa.resample(data.astype(float), orig_sr=sr, target_sr=22050)
                data = (data * 32767).astype("int16")
            os.unlink(wav_file)
            chunk_size = 4096
            for i in range(0, len(data), chunk_size):
                chunk = data[i:i+chunk_size].tobytes()
                yield chunk
        except Exception:
            pass

    async def speak(self, text: str, lang=None):
        """Convenience: speak full text (collects all chunks)."""
        async for _ in self.synthesize_stream(text, lang):
            pass  # chunks played externally


class StreamingTTSPlayer:
    """Plays streaming TTS chunks via sounddevice OutputStream."""

    def __init__(self, mic_stream):
        self.mic_stream = mic_stream
        self._playing = False
        self._abort = asyncio.Event()
        self._current_task = None

    async def play_stream(self, tts_generator):
        """Play TTS chunks from async generator. Can be interrupted."""
        self._playing = True
        self._abort.clear()
        try:
            async for chunk in tts_generator:
                if self._abort.is_set():
                    break
                await self.mic_stream.write_audio(chunk)
        finally:
            self._playing = False

    def abort(self):
        """Interrupt current playback."""
        self._abort.set()
        # Drain any queued audio so old speech doesn't bleed into new
        try:
            while not self.mic_stream._output_queue.empty():
                self.mic_stream._output_queue.get_nowait()
        except Exception:
            pass

    @property
    def is_playing(self):
        return self._playing


# Backward compatibility
def _speak_offline(text, lang="hi"):
    import pyttsx3
    import pythoncom
    import threading

    def _run():
        pythoncom.CoInitialize()
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 170)
            voices = engine.getProperty('voices')
            for v in voices:
                if lang == "hi" and "hindi" in v.name.lower():
                    engine.setProperty('voice', v.id)
                    break
            engine.say(text)
            engine.runAndWait()
        finally:
            pythoncom.CoUninitialize()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=15)


def _speak_online(text, lang="hi"):
    # edge-tts fallback (if needed)
    pass


TTS_ENABLED = True


def speak(text, lang="hi", emotion="neutral"):
    if not TTS_ENABLED or not text:
        return
    _speak_offline(text, lang)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, r".")
    asyncio.run(StreamingTTS().synthesize_stream("नमस्ते, मैं जार्विस हूँ।", "hi"))