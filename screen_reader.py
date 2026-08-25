import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_loader import CFG

try:
    import uiautomation as auto
    UIA_AVAILABLE = True
except ImportError:
    UIA_AVAILABLE = False

try:
    import mss
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False


def _clean_text(text):
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s\.\,\!\?\:\;\-\'\u0900-\u097F]", " ", text)
    return text.strip()


def _detect_lang(text):
    t = text.lower()
    hindi_words = [
        "hai", "ho", "mein", "tum", "aap", "bolo", "batao", "karo", "kaise",
        "acha", "theek", "nahi", "haan", "mera", "kaun", "abhi", "kal", "aaj",
        "parso", "kitna", "kitne", "kholo", "chalao", "kya", "kaun", "kaise",
    ]
    if any(w in t.split() for w in hindi_words):
        return "hi"
    ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
    total_letters = sum(1 for c in text if c.isalpha())
    if total_letters > 0 and ascii_letters / total_letters > 0.95:
        return "en"
    return "hi"


def _extract_text_uia(element, max_depth=10, current_depth=0):
    if current_depth > max_depth:
        return []
    texts = []
    try:
        name = element.Name
        if name and name.strip():
            texts.append(name.strip())
    except Exception:
        pass
    try:
        children = element.GetChildren()
        for child in children:
            texts.extend(_extract_text_uia(child, max_depth, current_depth + 1))
    except Exception:
        pass
    return texts


def read_active_window(max_chars=3000):
    if not UIA_AVAILABLE:
        return "UI Automation library not available. Install: pip install uiautomation"
    try:
        win = auto.GetForegroundControl()
        if not win:
            return "Koi active window nahi mila."
        texts = _extract_text_uia(win)
        full_text = " ".join(texts)
        full_text = _clean_text(full_text)
        if not full_text:
            return "Active window se koi text nahi mila."
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "... (baaki kat diya)"
        lang = _detect_lang(full_text)
        return {"text": full_text, "lang": lang, "source": "uiautomation"}
    except Exception as e:
        return f"Screen read error: {type(e).__name__}: {e}"


def read_full_screen(max_chars=4000):
    if not UIA_AVAILABLE:
        return "UI Automation library not available. Install: pip install uiautomation"
    try:
        desktop = auto.GetRootControl()
        texts = _extract_text_uia(desktop, max_depth=8)
        full_text = " ".join(texts)
        full_text = _clean_text(full_text)
        if not full_text:
            return "Screen se koi text nahi mila."
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "... (baaki kat diya)"
        lang = _detect_lang(full_text)
        return {"text": full_text, "lang": lang, "source": "uiautomation"}
    except Exception as e:
        return f"Full screen read error: {type(e).__name__}: {e}"


def read_selection():
    import pyautogui
    import pyperclip
    try:
        pyautogui.hotkey("ctrl", "c")
        import time
        time.sleep(0.15)
        text = pyperclip.paste()
        if not text or not text.strip():
            return "Clipboard khali hai. Kuch select karke Ctrl+C dabayein."
        text = _clean_text(text)
        lang = _detect_lang(text)
        return {"text": text, "lang": lang, "source": "clipboard"}
    except Exception as e:
        return f"Selection read error: {type(e).__name__}: {e}"


def read_screen(mode="active", max_chars=3000):
    cfg = CFG.get("screen_reader", {})
    if not cfg.get("enabled", True):
        return "Screen reader disabled in config."
    if mode == "full":
        result = read_full_screen(max_chars)
    elif mode == "selection":
        result = read_selection()
    else:
        result = read_active_window(max_chars)
    
    if isinstance(result, dict):
        text = result.get("text", "")
        if text:
            return f"Screen text: {text}"
        return "Screen se koi text nahi mila."
    return result


if __name__ == "__main__":
    print("Testing screen reader...")
    print("Active window:")
    result = read_active_window()
    if isinstance(result, dict):
        print(f"  Lang: {result['lang']}")
        print(f"  Text: {result['text'][:200]}...")
    else:
        print(f"  Error: {result}")