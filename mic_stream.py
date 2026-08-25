import asyncio
import collections
import numpy as np
import sounddevice as sd


class AsyncMicStream:
    """Async mic stream with callback-based I/O using sounddevice."""

    def __init__(self, blocksize=4000, samplerate=16000, device=None):
        self.blocksize = blocksize
        self.samplerate = samplerate
        self._device = device
        self._input_queue = asyncio.Queue(maxsize=64)
        self._output_queue = asyncio.Queue(maxsize=64)
        self._input_stream = None
        self._output_stream = None
        self._running = False

    async def start_input(self):
        """Start microphone input stream (callback-based)."""
        if self._running:
            return

        def callback(indata, frames, time_info, status):
            if status:
                pass  # overflow/underflow warnings
            # Convert to int16 bytes (Vosk expects int16 PCM)
            try:
                if self._dtype == "float32":
                    audio = (np.frombuffer(indata, dtype=np.float32) * 32767).astype(np.int16)
                else:
                    audio = np.frombuffer(indata, dtype=np.int16)
                self._input_queue.put_nowait(audio.tobytes())
            except asyncio.QueueFull:
                pass  # drop frame if queue full

        # Find working input device + matching samplerate/dtype
        result = await self._find_working_input_device()
        if result is None:
            raise RuntimeError("No working microphone found")

        device, samplerate, dtype = result
        self._device = device
        self.samplerate = samplerate
        self._dtype = dtype

        self._input_stream = sd.RawInputStream(
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            dtype=self._dtype,
            channels=1,
            latency="high",
            device=self._device,
            callback=callback,
        )
        self._input_stream.start()
        self._running = True

    async def _find_working_input_device(self):
        """Find first working input device across all host APIs.

        Tries multiple sample rates (preferring 16000 for Vosk) and dtypes.
        Returns (device_index, samplerate, dtype) or None.
        """
        # Candidate sample rates: Vosk wants 16000, but some devices
        # (e.g. Bluetooth HFP) only support 8000.
        sample_rates = [16000, 44100, 48000, 8000, 22050]
        dtypes = ["int16", "float32"]

        input_devices = []
        for i, d in enumerate(sd.query_devices()):
            if d.get("max_input_channels", 0) <= 0:
                continue
            try:
                host = sd.query_hostapis(d["hostapi"])["name"]
            except Exception:
                host = ""
            # Prefer non-WDM-KS host APIs (more reliable on Windows)
            preferred = host in ("MME", "Windows WASAPI", "Windows DirectSound")
            input_devices.append((i, host, preferred))

        # Sort: preferred hosts first, then any
        input_devices.sort(key=lambda x: (not x[2], x[0]))

        import queue
        import time

        for dev, host, _pref in input_devices:
            # Determine device default samplerate
            try:
                dev_sr = int(sd.query_devices(dev)["default_samplerate"])
            except Exception:
                dev_sr = 44100
            rates_to_try = sorted(set([dev_sr] + sample_rates), reverse=True)
            for sr in rates_to_try:
                for dtype in dtypes:
                    try:
                        q = queue.Queue()
                        def cb(indata, frames, time_info, status):
                            q.put(bytes(indata))
                        stream = sd.RawInputStream(
                            samplerate=sr,
                            blocksize=self.blocksize,
                            dtype=dtype,
                            channels=1,
                            latency="high",
                            device=dev,
                            callback=cb,
                        )
                        stream.start()
                        # Wait briefly to confirm the stream actually starts
                        deadline = time.time() + 0.4
                        started = False
                        while time.time() < deadline:
                            if not q.empty():
                                started = True
                                break
                            time.sleep(0.02)
                        stream.stop()
                        stream.close()
                        if started:
                            # Prefer 16000 if the device supports it
                            if sr == 16000:
                                return (dev, 16000, dtype)
                            # Otherwise return first working config
                            return (dev, sr, dtype)
                    except Exception:
                        continue
        return None

    async def read_audio(self):
        """Async read audio chunk from input queue."""
        if not self._running:
            await self.start_input()
        return await self._input_queue.get()

    async def start_output(self, samplerate=22050):
        """Start audio output stream for TTS playback."""
        self._output_samplerate = samplerate

        def output_callback(outdata, frames, time_info, status):
            try:
                chunk = self._output_queue.get_nowait()
                if len(chunk) < frames * 2:  # pad if needed
                    chunk += b"\x00" * (frames * 2 - len(chunk))
                outdata[:] = np.frombuffer(chunk, dtype=np.int16).reshape(-1, 1)
            except asyncio.QueueEmpty:
                outdata.fill(0)

        self._output_stream = sd.RawOutputStream(
            samplerate=samplerate,
            blocksize=1024,
            dtype="int16",
            channels=1,
            latency="low",
            callback=output_callback,
        )
        self._output_stream.start()

    async def write_audio(self, chunk: bytes):
        """Queue audio chunk for playback."""
        if self._output_stream is None:
            await self.start_output()
        await self._output_queue.put(chunk)

    async def stop(self):
        """Stop all streams."""
        if self._input_stream:
            self._input_stream.stop()
            self._input_stream.close()
            self._input_stream = None
        if self._output_stream:
            self._output_stream.stop()
            self._output_stream.close()
            self._output_stream = None
        self._running = False

    async def __aenter__(self):
        await self.start_input()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()