import os
import sys
import json
import tempfile
import textwrap
import subprocess
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_loader import CFG

try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def _get_ffmpeg_path():
    return CFG.get("youtube", {}).get("video_creation", {}).get("ffmpeg_path", "ffmpeg")


def _get_video_config():
    return CFG.get("youtube", {}).get("video_creation", {})


def _generate_script(topic, duration_min=2, language="hi"):
    cfg = _get_video_config()
    
    if language == "hi":
        prompt = f"""Tum ek YouTube video script writer ho. Topic: "{topic}".
Duration: {duration_min} minutes.
Language: Hindi/Hinglish.

Rules:
- Script ko {duration_min * 150} words ke aas-paas rakho
- 5-7 slides/sections mein baanto
- Har slide ka title aur content do
- Engaging, conversational tone (Hinglish)
- Hook (pehle 5 sec), main content, CTA (subscribe/like)
- JSON format return karo:
{{"slides": [
  {{"title": "Slide 1 Title", "content": "Slide 1 content...", "duration": 30}},
  ...
]}}"""
    else:
        prompt = f"""You are a YouTube script writer. Topic: "{topic}".
Duration: {duration_min} minutes.
Language: English.

Rules:
- Script ~{duration_min * 150} words
- 5-7 slides/sections
- Each slide: title, content, duration
- Engaging, conversational tone
- Hook, main content, CTA
- Return JSON:
{{"slides": [
  {{"title": "Slide 1 Title", "content": "Slide 1 content...", "duration": 30}},
  ...
]}}"""

    try:
        import llm
        resp, _ = llm.chat([
            {"role": "system", "content": "You are a YouTube script writer. Return only valid JSON."},
            {"role": "user", "content": prompt}
        ], tools=None, tier="cloud_mid")
        content = resp["content"]
        if content:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
    except Exception as e:
        print(f"LLM script generation failed: {e}")

    return _fallback_script(topic, duration_min, language)


def _fallback_script(topic, duration_min, language):
    slides_per_min = 3
    total_slides = max(5, min(7, duration_min * slides_per_min))
    slide_duration = (duration_min * 60) // total_slides

    if language == "hi":
        slides = [
            {"title": f"Namaste! Aaj ka topic: {topic}", "content": f"Dosto, aaj hum baat karenge {topic} ke baare mein. Ye bahut interesting topic hai.", "duration": slide_duration},
            {"title": "Kyun important hai?", "content": f"{topic} aaj kal bahut relevant hai. Har kisi ko iske baare mein pata hona chahiye.", "duration": slide_duration},
            {"title": "Main points", "content": f"Chaliye {topic} ke main points samajhte hain. Pehla point...", "duration": slide_duration},
            {"title": "Details aur examples", "content": "Iske saath kuch examples bhi dete hain taaki aasani se samajh aaye.", "duration": slide_duration},
            {"title": "Summary", "content": f"Toh dosto, {topic} ke baare mein ye thi hamari baat. Umeed hai pasand aayi.", "duration": slide_duration},
            {"title": "Subscribe & Like!", "content": "Agar video pasand aayi toh like karein, subscribe karein, aur bell icon dabayein!", "duration": slide_duration},
        ]
    else:
        slides = [
            {"title": f"Welcome! Today's topic: {topic}", "content": f"Hey everyone, today we're talking about {topic}. This is a really interesting topic.", "duration": slide_duration},
            {"title": "Why it matters", "content": f"{topic} is very relevant today. Everyone should know about it.", "duration": slide_duration},
            {"title": "Key points", "content": f"Let's understand the main points about {topic}. First point...", "duration": slide_duration},
            {"title": "Details & examples", "content": "Let's also look at some examples to make it easier to understand.", "duration": slide_duration},
            {"title": "Summary", "content": f"So that was our talk about {topic}. Hope you liked it.", "duration": slide_duration},
            {"title": "Subscribe & Like!", "content": "If you liked the video, please like, subscribe, and hit the bell icon!", "duration": slide_duration},
        ]

    return {"slides": slides[:total_slides]}


def _create_slide_image(title, content, slide_num, total_slides, output_path, language="hi"):
    if not PIL_AVAILABLE:
        return False

    cfg = _get_video_config()
    width = 1920
    height = 1080
    bg_color = cfg.get("bg_color", "#1a1a2e")
    text_color = cfg.get("text_color", "#ffffff")
    font_size = cfg.get("font_size", 48)

    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    try:
        font_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segui.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        font = None
        for fp in font_paths:
            if os.path.exists(fp):
                font = ImageFont.truetype(fp, font_size)
                break
        if font is None:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    margin = 100
    max_width = width - 2 * margin

    def draw_wrapped_text(text, y_start, font_size_mult=1.0, color=text_color, center=True):
        fs = int(font_size * font_size_mult)
        try:
            f = ImageFont.truetype(font.path, fs) if hasattr(font, 'path') else font
        except Exception:
            f = font

        lines = textwrap.wrap(text, width=50)
        y = y_start
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=f)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            x = (width - w) // 2 if center else margin
            draw.text((x, y), line, font=f, fill=color)
            y += h + 10
        return y

    y = 150
    draw_wrapped_text(title, y, 1.5, "#ffd700")
    y += 120

    draw.line([(margin, y), (width - margin, y)], fill="#ffd700", width=3)
    y += 30

    draw_wrapped_text(content, y, 1.0, text_color)

    y = height - 100
    draw_wrapped_text(f"Slide {slide_num} of {total_slides}", y, 0.7, "#888888")

    try:
        img.save(output_path, quality=95)
        return True
    except Exception as e:
        print(f"Slide save error: {e}")
        return False


async def _generate_tts_audio(text, output_path, language="hi"):
    try:
        import edge_tts
        voice = "hi-IN-MadhurNeural" if language == "hi" else "en-US-GuyNeural"
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return True
    except Exception as e:
        print(f"TTS error: {e}")
        return False


def _get_audio_duration(audio_path):
    try:
        probe = ffmpeg.probe(audio_path)
        return float(probe['format']['duration'])
    except Exception:
        return 5.0


def create_video_from_topic(topic, duration_min=2, language="hi", output_path=None):
    if not FFMPEG_AVAILABLE:
        return "ffmpeg-python not installed. Run: pip install ffmpeg-python"

    if output_path is None:
        output_path = os.path.join(tempfile.gettempdir(), f"jarvis_video_{topic.replace(' ', '_')}.mp4")

    print(f"Generating script for: {topic}...")
    script = _generate_script(topic, duration_min, language)
    slides = script.get("slides", [])

    if not slides:
        return "Script generation failed."

    print(f"Created {len(slides)} slides. Generating assets...")

    segment_files = []

    for i, slide in enumerate(slides):
        slide_num = i + 1
        total = len(slides)

        img_path = os.path.join(tempfile.gettempdir(), f"slide_{slide_num}.png")
        if not _create_slide_image(slide["title"], slide["content"], slide_num, total, img_path, language):
            return f"Failed to create slide {slide_num} image."

        audio_path = os.path.join(tempfile.gettempdir(), f"audio_{slide_num}.mp3")
        asyncio.run(_generate_tts_audio(slide["content"], audio_path, language))
        if not os.path.exists(audio_path):
            return f"Failed to generate audio for slide {slide_num}."

        dur = _get_audio_duration(audio_path)

        segment_path = os.path.join(tempfile.gettempdir(), f"segment_{slide_num}.mp4")
        try:
            video_input = ffmpeg.input(img_path, loop=1, framerate=30, t=dur)
            audio_input = ffmpeg.input(audio_path)
            (
                ffmpeg
                .output(video_input, audio_input, segment_path, vcodec="libx264", pix_fmt="yuv420p", r=30, acodec="aac", audio_bitrate="128k", preset="medium", crf=23, shortest=None)
                .run(overwrite_output=True, quiet=True)
            )
            segment_files.append(segment_path)
        except ffmpeg.Error as e:
            return f"Segment {slide_num} creation failed: {e.stderr.decode() if e.stderr else str(e)}"

    print("Concatenating segments...")

    try:
        concat_file = os.path.join(tempfile.gettempdir(), "segments_concat.txt")
        with open(concat_file, "w", encoding="utf-8") as f:
            for seg in segment_files:
                f.write(f"file '{seg}'\n")

        (
            ffmpeg
            .input(concat_file, f="concat", safe=0)
            .output(output_path, vcodec="copy", acodec="copy")
            .run(overwrite_output=True, quiet=True)
        )

        for f in segment_files + [concat_file]:
            try:
                os.remove(f)
            except Exception:
                pass

        for i in range(len(slides)):
            img_path = os.path.join(tempfile.gettempdir(), f"slide_{i+1}.png")
            audio_path = os.path.join(tempfile.gettempdir(), f"audio_{i+1}.mp3")
            try:
                if os.path.exists(img_path):
                    os.remove(img_path)
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception:
                pass

        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            return f"Video created: {output_path} ({size_mb:.1f} MB)"
        else:
            return "Video creation failed - output not found."

    except ffmpeg.Error as e:
        return f"FFmpeg concat error: {e.stderr.decode() if e.stderr else str(e)}"
    except Exception as e:
        return f"Video assembly error: {type(e).__name__}: {e}"


def create_video_from_script(script_json, language="hi", output_path=None):
    if isinstance(script_json, str):
        try:
            script = json.loads(script_json)
        except Exception:
            return "Invalid script JSON."
    else:
        script = script_json

    slides = script.get("slides", [])
    if not slides:
        return "No slides in script."

    if output_path is None:
        output_path = os.path.join(tempfile.gettempdir(), f"jarvis_video_custom.mp4")

    print(f"Creating video from custom script ({len(slides)} slides)...")

    segment_files = []

    for i, slide in enumerate(slides):
        slide_num = i + 1
        total = len(slides)

        img_path = os.path.join(tempfile.gettempdir(), f"slide_{slide_num}.png")
        if not _create_slide_image(slide.get("title", ""), slide.get("content", ""), slide_num, total, img_path, language):
            return f"Failed to create slide {slide_num} image."

        audio_path = os.path.join(tempfile.gettempdir(), f"audio_{slide_num}.mp3")
        asyncio.run(_generate_tts_audio(slide.get("content", ""), audio_path, language))
        if not os.path.exists(audio_path):
            return f"Failed to generate audio for slide {slide_num}."

        dur = _get_audio_duration(audio_path)

        segment_path = os.path.join(tempfile.gettempdir(), f"segment_{slide_num}.mp4")
        try:
            video_input = ffmpeg.input(img_path, loop=1, framerate=30, t=dur)
            audio_input = ffmpeg.input(audio_path)
            (
                ffmpeg
                .output(video_input, audio_input, segment_path, vcodec="libx264", pix_fmt="yuv420p", r=30, acodec="aac", audio_bitrate="128k", preset="medium", crf=23, shortest=None)
                .run(overwrite_output=True, quiet=True)
            )
            segment_files.append(segment_path)
        except ffmpeg.Error as e:
            return f"Segment {slide_num} creation failed: {e.stderr.decode() if e.stderr else str(e)}"

    print("Concatenating segments...")

    try:
        concat_file = os.path.join(tempfile.gettempdir(), "segments_concat.txt")
        with open(concat_file, "w", encoding="utf-8") as f:
            for seg in segment_files:
                f.write(f"file '{seg}'\n")

        (
            ffmpeg
            .input(concat_file, f="concat", safe=0)
            .output(output_path, vcodec="copy", acodec="copy")
            .run(overwrite_output=True, quiet=True)
        )

        for f in segment_files + [concat_file]:
            try:
                os.remove(f)
            except Exception:
                pass

        for i in range(len(slides)):
            img_path = os.path.join(tempfile.gettempdir(), f"slide_{i+1}.png")
            audio_path = os.path.join(tempfile.gettempdir(), f"audio_{i+1}.mp3")
            try:
                if os.path.exists(img_path):
                    os.remove(img_path)
                if os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception:
                pass

        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            return f"Video created: {output_path} ({size_mb:.1f} MB)"
        else:
            return "Video creation failed - output not found."

    except ffmpeg.Error as e:
        return f"FFmpeg concat error: {e.stderr.decode() if e.stderr else str(e)}"
    except Exception as e:
        return f"Video assembly error: {type(e).__name__}: {e}"


if __name__ == "__main__":
    print("Testing video creator...")
    result = create_video_from_topic("AI ke fayde", duration_min=1, language="hi")
    print(result)