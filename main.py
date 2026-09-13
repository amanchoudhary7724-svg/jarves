import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
)
# Suppress noisy third-party logs
logging.getLogger("comtypes").setLevel(logging.WARNING)
logging.getLogger("comtypes.client").setLevel(logging.WARNING)
logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.WARNING)
import argparse
import asyncio
import os
import sys

# Fix Windows console encoding for emoji/unicode output from LLM
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tts import speak, StreamingTTS, StreamingTTSPlayer, TTS_ENABLED
from agent import JarvisAgent, _detect_lang
from stt import stt_stream, _detect_lang as _stt_detect_lang
from mic_stream import AsyncMicStream


def _speak(*args, **kwargs):
    if TTS_ENABLED:
        try:
            speak(*args, **kwargs)
        except Exception as e:
            print(f"[TTS skip] {e}")


async def live_mode():
    """Fully async live voice conversation with wake-word gating."""
    try:
        from mic_stream import AsyncMicStream
    except (ImportError, ModuleNotFoundError) as e:
        print(f"[JARVIS] Voice mode nahi chali: {e}")
        print("[JARVIS] Voice deps (sounddevice/vosk/piper) install nahi hain.")
        return False

    agent = JarvisAgent()
    tts = StreamingTTS()
    tts_player = StreamingTTSPlayer(mic)
    agent.set_tts_player(tts_player)

    # Wake word detector (0.4 tuned for real-mic audio; TTS tests hit ~1.0,
    # live voice peaks ~0.45-0.6 due to room noise/distance)
    from wakeword_detector import create_wake_word_detector
    wake_detector = create_wake_word_detector("hey_jarvis", threshold=0.4)

    print("=" * 50)
    print("  JARVIS VOICE LIVE CONVERSATION (Hindi + English)")
    print("  Wake word: 'Hey Jarvis' (ya seedha boliye)")
    print("  Beech mein bhi bol sakte ho - main sununga")
    print("=" * 50)

    # Gain 10x: Bluetooth HFP mics capture very quietly (~0.4% peak even
    # speaking loudly); digital amplification brings speech into STT range
    mic = AsyncMicStream(gain=50.0)

    try:
        await mic.start_input()
    except RuntimeError as e:
        print(f"\n[JARVIS] Microphone shuru nahi ho saka: {e}")
        print("[JARVIS] Koi working mic nahi mila (Bluetooth HFP driver issue ho sakta hai).")
        await mic.stop()
        return False

    print("\n[JARVIS] Wake word ka intezaar... ('Hey Jarvis' bolo)")

    stt_gen = None
    try:
        tts_player_task = None
        # ONE STT generator reused across turns (avoids reloading VAD/ONNX
        # session every turn and prevents async-generator leaks)
        stt_gen = stt_stream(mic, lang="hi", pause_sec=1.5, normalize=True)

        # Main loop: wake word -> conversation turn
        while True:
            # Drain any mic backlog (e.g. echo of Jarvis's own TTS) so stale
            # audio doesn't false-trigger the wake word or pollute the next turn
            try:
                q = getattr(mic, "_input_queue", None)
                if q is not None:
                    while not q.empty():
                        q.get_nowait()
            except Exception:
                pass

            # Wake word listening phase
            print("\n[JARVIS] Sun raha hoon... (wake word ka intezaar)")
            wake_detected = False
            # Buffer to accumulate audio for 1280-sample windows
            audio_buffer = bytearray()
            # Read chunks for wake word detection
            while not wake_detected:
                chunk = await mic.read_audio()
                # Resample to 16kHz if needed for wake word model
                from stt import resample_audio
                if hasattr(mic, 'samplerate') and mic.samplerate != 16000:
                    chunk = resample_audio(chunk, mic.samplerate, 16000)
                audio_buffer.extend(chunk)
                # Process in 1280-sample windows (2560 bytes)
                while len(audio_buffer) >= 2560:
                    window = bytes(audio_buffer[:2560])
                    audio_buffer = audio_buffer[2560:]
                    score = wake_detector.predict(window)
                    if score > 0.15:
                        import numpy as _np
                        peak = int(_np.abs(_np.frombuffer(window, dtype=np.int16)).max())
                        print(f"\n  [wake] score={score:.3f} peak={peak}")
                    if score >= 0.4:
                        wake_detected = True
                        print("\n[JARVIS] Wake word detected! Sun raha hoon...")
                        break
                await asyncio.sleep(0.005)

            # Conversation turn: run STT for one utterance (reuse stt_gen)
            final_text = None
            async def collect_one_utterance():
                nonlocal final_text
                async for partial, final in stt_gen:
                    if partial:
                        print(f"  [partial] {partial}", end="\r", flush=True)
                    if final:
                        final_text = final
                        return
            try:
                await asyncio.wait_for(collect_one_utterance(), timeout=10)
            except asyncio.TimeoutError:
                print("\n[JARVIS] Kuch suna nahi, wapas wake word mode mein...")
                continue

            if not final_text:
                continue

            print(f"\n[Aapne kaha]: {final_text}")
            lang = _stt_detect_lang(final_text)

            # Interrupt any ongoing TTS
            tts_player.abort()

            # Process through agent
            resp, emotion = await agent.handle(final_text, lang=lang)
            print(f"[Jarvis]: {resp} [{emotion}]")

            # Stream TTS response (interruptible)
            if tts_player_task is not None and not tts_player_task.done():
                tts_player_task.cancel()
                try:
                    await tts_player_task
                except asyncio.CancelledError:
                    pass
            tts_gen_resp = StreamingTTS().synthesize_stream(resp, lang=lang)
            tts_player_task = asyncio.create_task(tts_player.play_stream(tts_gen_resp))

            # Wait for TTS to complete or be interrupted
            try:
                await tts_player_task
            except asyncio.CancelledError:
                pass

            # Reset wake word detector for next turn
            wake_detector.reset()

    except KeyboardInterrupt:
        print("\n[JARVIS] Bye!")
        _speak("Alvida, phir milte hain.", lang="hi")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
    finally:
        # Close the STT async generator cleanly
        try:
            if stt_gen is not None:
                await stt_gen.aclose()
        except Exception:
            pass
        await mic.stop()
    return True


async def _text_mode_async():
    agent = JarvisAgent()
    print("=" * 50)
    print("  JARVIS (Hindi + English)")
    print("  Type your message, 'voice' for mic, 'quit' to exit")
    print("=" * 50)
    while True:
        try:
            user = input("\nAap: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user:
            continue
        if user.lower() in ("quit", "exit", "q"):
            break
        if user.lower() == "voice":
            await live_mode()
            continue
        lang = _detect_lang(user)
        try:
            resp, emotion = await agent.handle(user, lang=lang)
        except Exception as e:
            resp, emotion = f"Error: {e}", "neutral"
        print(f"Jarvis: {resp} [{emotion}]")
        try:
            _speak(resp, lang=lang, emotion=emotion)
        except Exception:
            pass


def text_mode():
    asyncio.run(_text_mode_async())


async def _one_shot_async():
    from mic_stream import AsyncMicStream
    from stt import stt_stream, _detect_lang

    agent = JarvisAgent()
    print("Listening... (10 sec)")
    try:
        mic = AsyncMicStream(gain=10.0)
        await mic.start_input()
    except RuntimeError as e:
        print(f"Microphone nahi chala: {e}")
        return
    try:
        stt_gen = stt_stream(mic, lang="hi", pause_sec=1.5, normalize=True)
        final_text = None
        async def collect():
            nonlocal final_text
            async for partial, final in stt_gen:
                if final:
                    final_text = final
                    return
        try:
            await asyncio.wait_for(collect(), timeout=10)
        except asyncio.TimeoutError:
            pass
    finally:
        await mic.stop()

    if not final_text:
        print("Kuch suna nahi.")
        return
    lang = _detect_lang(final_text)
    print(f"Aapne kaha ({lang}): {final_text}")
    resp, emotion = await agent.handle(final_text, lang=lang)
    print(f"Jarvis: {resp} [{emotion}]")
    _speak(resp, lang=lang, emotion=emotion)


def one_shot():
    asyncio.run(_one_shot_async())


def main():
    global TTS_ENABLED
    parser = argparse.ArgumentParser(description="JARVIS Voice Assistant")
    parser.add_argument("--voice", action="store_true", help="Live voice mode (needs working mic)")
    parser.add_argument("--voice-once", action="store_true", help="One-shot: listen once, respond")
    parser.add_argument("--no-tts", action="store_true", help="TTS off (test logic without audio)")
    args = parser.parse_args()

    if args.no_tts:
        TTS_ENABLED = False

    if args.voice:
        ok = asyncio.run(live_mode())
        if not ok:
            print("\n[JARVIS] Voice mic unavailable.\n")
            text_mode()
    elif args.voice_once:
        one_shot()
    else:
        text_mode()


if __name__ == "__main__":
    main()
