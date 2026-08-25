import os
import sys
import textwrap
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_loader import CFG

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def _get_thumb_config():
    return CFG.get("youtube", {}).get("thumbnail", {})


def _load_font(size):
    cfg = _get_thumb_config()
    font_path = cfg.get("font_path", "C:/Windows/Fonts/arial.ttf")
    font_paths = [
        font_path,
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segui.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _wrap_text(draw, text, font, max_width):
    lines = []
    words = text.split()
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def generate_thumbnail(title, output_path=None, style="modern", language="hi"):
    if not PIL_AVAILABLE:
        return "PIL not installed. Run: pip install pillow"

    if output_path is None:
        output_path = os.path.join(tempfile.gettempdir(), f"thumbnail_{title.replace(' ', '_')}.jpg")

    cfg = _get_thumb_config()
    width = cfg.get("width", 1280)
    height = cfg.get("height", 720)

    img = Image.new("RGB", (width, height), "#0a0a1a")
    draw = ImageDraw.Draw(img)

    if style == "modern":
        for y in range(height):
            r = int(10 + (y / height) * 30)
            g = int(10 + (y / height) * 20)
            b = int(26 + (y / height) * 50)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        for _ in range(50):
            import random
            x = random.randint(0, width)
            y = random.randint(0, height)
            r = random.randint(30, 60)
            draw.ellipse([x, y, x+r, y+r], fill=(255, 215, 0, 50))

    elif style == "minimal":
        draw.rectangle([0, 0, width, height], fill="#1a1a2e")
        draw.rectangle([0, 0, 8, height], fill="#ffd700")

    elif style == "bold":
        draw.rectangle([0, 0, width, height], fill="#0d0d1a")
        draw.rectangle([0, height//2, width, height], fill="#1a0a2e")

    title_font_size = 72
    title_font = _load_font(title_font_size)

    max_text_width = width - 120
    lines = _wrap_text(draw, title, title_font, max_text_width)

    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        line_heights.append(bbox[3] - bbox[1])

    total_text_height = sum(line_heights) + (len(lines) - 1) * 15
    start_y = (height - total_text_height) // 2

    y = start_y
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (width - w) // 2

        shadow_offset = 4
        draw.text((x + shadow_offset, y + shadow_offset), line, font=title_font, fill="#000000")

        if i == 0:
            draw.text((x, y), line, font=title_font, fill="#ffd700")
        else:
            draw.text((x, y), line, font=title_font, fill="#ffffff")

        y += h + 15

    if language == "hi":
        badge_text = "HINDI"
    else:
        badge_text = "ENGLISH"

    badge_font = _load_font(24)
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    bw = bbox[2] - bbox[0]
    bh = bbox[3] - bbox[1]
    bx = width - bw - 40
    by = height - bh - 40
    draw.rounded_rectangle([bx-10, by-5, bx+bw+10, by+bh+5], radius=8, fill="#ffd700")
    draw.text((bx, by), badge_text, font=badge_font, fill="#000000")

    try:
        img.save(output_path, quality=95)
        return f"Thumbnail created: {output_path}"
    except Exception as e:
        return f"Thumbnail save error: {type(e).__name__}: {e}"


def generate_thumbnail_with_bg(title, bg_image_path=None, output_path=None, language="hi"):
    if not PIL_AVAILABLE:
        return "PIL not installed."

    if output_path is None:
        output_path = os.path.join(tempfile.gettempdir(), f"thumbnail_{title.replace(' ', '_')}.jpg")

    cfg = _get_thumb_config()
    width = cfg.get("width", 1280)
    height = cfg.get("height", 720)

    if bg_image_path and os.path.exists(bg_image_path):
        try:
            bg = Image.open(bg_image_path).convert("RGB")
            bg = bg.resize((width, height), Image.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(radius=3))
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, 180))
            img = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
        except Exception:
            img = Image.new("RGB", (width, height), "#0a0a1a")
    else:
        img = Image.new("RGB", (width, height), "#0a0a1a")

    draw = ImageDraw.Draw(img)

    title_font_size = 72
    title_font = _load_font(title_font_size)

    max_text_width = width - 120
    lines = _wrap_text(draw, title, title_font, max_text_width)

    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        line_heights.append(bbox[3] - bbox[1])

    total_text_height = sum(line_heights) + (len(lines) - 1) * 15
    start_y = (height - total_text_height) // 2

    y = start_y
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = (width - w) // 2

        shadow_offset = 4
        draw.text((x + shadow_offset, y + shadow_offset), line, font=title_font, fill="#000000")

        if i == 0:
            draw.text((x, y), line, font=title_font, fill="#ffd700")
        else:
            draw.text((x, y), line, font=title_font, fill="#ffffff")

        y += h + 15

    try:
        img.save(output_path, quality=95)
        return f"Thumbnail created: {output_path}"
    except Exception as e:
        return f"Thumbnail save error: {type(e).__name__}: {e}"


if __name__ == "__main__":
    print("Testing thumbnail maker...")
    print(generate_thumbnail("AI ke 5 Fayde jo Aap Nahi Jaante", style="modern", language="hi"))
    print(generate_thumbnail("5 AI Benefits You Didn't Know", style="minimal", language="en"))
    print(generate_thumbnail("Secret AI Tools 2026", style="bold", language="hi"))