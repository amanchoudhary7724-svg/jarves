import asyncio
import re
from collections import deque
from datetime import datetime

import llm
from tools.registry import execute, get_schemas
from tts import _detect_emotion_from_text, StreamingTTSPlayer


def _truncate_response(text: str, lang: str, max_lines: int = 2) -> str:
    """Truncate response to max_lines (split by newline or sentence)."""
    if not text:
        return text
    # Split by newlines first
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if len(lines) <= max_lines:
        return '\n'.join(lines)
    # If too many lines, take first max_lines and truncate
    truncated = ' '.join(lines[:max_lines])
    # Ensure it ends with punctuation
    if truncated and truncated[-1] not in '.।?!':
        truncated += '.'
    return truncated

HISTORY_MAX = 12

SYSTEM_PROMPTS = {
    "hi": """Tum Jarvis ho, ek intelligent AI voice assistant. Tum Hindi/Hinglish mein baat karte ho.

RULES:
- Jawab Hinglish mein do (Hindi + English mix), **ek sentence mein** (max 2 lines)
- Greeting: simple "Namaste" ya "Haan boliye"
- Agar koi action karna ho toh seedha batao, mat pucho
- Code likhna ho toh screen pe dikha do
- Action maange jaane par **always** use karein tools (open_app, close_app, youtube_play_video, etc.), manual instructions mat dein.
- **Kabhi bhi 2 lines se zyada mat likho.**

EXAMPLES:
User: "youtube par romantic song play karo"
Jarvis: "Romantic song YouTube pe chala raha hoon."

User: "time kya hai?"
Jarvis: "Abhi 2:30 dopahar hain."

User: "brightness badhao"
Jarvis: "Screen brightness badha di.""",
    "en": """You are Jarvis, an intelligent AI voice assistant. You speak English.

RULES:
- Keep answers short and crisp: **ONE sentence** (max 2 lines)
- Greeting: simple "Hello!" or "Yes sir?"
- If an action is needed, just say you're doing it, don't ask
- Show code on screen instead of reading it out loud
- For open/play/system-control requests, ALWAYS use the appropriate tool, never give manual instructions.
- **Never exceed 2 lines.**

EXAMPLES:
User: "play romantic song on youtube"
Jarvis: "Playing romantic song on YouTube."

User: "what time is it?"
Jarvis: "It's 2:30 PM right now."

User: "increase brightness"
Jarvis: "Screen brightness increased."""
}

_greetings_hi = ["namaste", "namaskar", "kaise ho", "kya haal", "sup bhai", "kaisa hai"]
_greetings_en = ["hello jarvis", "hey jarvis", "hi jarvis", "good morning", "good evening", "are you there", "you there"]
_stop_words = ["quit", "exit", "bye", "alvida"]

_days_hi = ["Somvaar", "Mangalvaar", "Budhvaar", "Guruvaar", "Shukravaar", "Shanivaar", "Ravivaar"]
_days_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_months_hi = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def _detect_lang(text):
    t = text.lower()
    hindi_words = [
        "kya", "hai", "ho", "mein", "tum", "aap", "bolo", "batao", "karo",
        "kaise", "acha", "theek", "nahi", "haan", "mera", "kaun", "abhi",
        "kal", "aaj", "parso", "kitna", "kitne", "kholo", "chalao",
    ]
    if any(w in t.split() for w in hindi_words):
        return "hi"
    ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
    total_letters = sum(1 for c in text if c.isalpha())
    if total_letters > 0 and ascii_letters / total_letters > 0.95:
        return "en"
    return "hi"


def _time_response(lang):
    now = datetime.now()
    h12 = now.hour % 12 or 12
    if lang == "en":
        ampm = "AM" if now.hour < 12 else "PM"
        return f"It's {h12}:{now.minute:02d} {ampm} right now."
    ampm = "subah" if now.hour < 12 else ("dopahar" if now.hour < 17 else ("shaam" if now.hour < 21 else "raat"))
    return f"Abhi {h12}:{now.minute:02d} {ampm} ho rahe hain."


def _date_response(lang):
    now = datetime.now()
    months_en = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    if lang == "en":
        return f"Today is {_days_en[now.weekday()]}, {months_en[now.month - 1]} {now.day}, {now.year}."
    return f"Aaj {_days_hi[now.weekday()]} hai, {now.day} {_months_hi[now.month - 1]} {now.year}."


# ---- Rules and helper functions (copied from original to avoid circular import) ----
_greetings_hi = ["namaste", "namaskar", "kaise ho", "kya haal", "sup bhai"]
_greetings_en = ["hello jarvis", "hey jarvis", "hi jarvis", "good morning", "good evening", "are you there", "you there"]
_stop_words = ["quit", "exit", "bye", "alvida"]

_days_hi = ["Somvaar", "Mangalvaar", "Budhvaar", "Guruvaar", "Shukravaar", "Shanivaar", "Ravivaar"]
_days_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_months_hi = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]



RULES = [
    # Window management
    {"patterns": [r"\b(window|tab|windo)\b.*\b(band|close)\b", r"\b(band|close)\b.*\b(window|tab)\b"],
     "handler": lambda m: ("close_window", {})},
    {"patterns": [r"\b(window|tab|windo)\b.*\b(minimi[sz]e|chhota|minimise)\b"],
     "handler": lambda m: ("minimize_window", {})},
    {"patterns": [r"\b(window|tab|windo)\b.*\b(maximi[sz]e|fullscreen|full screen|bada)\b"],
     "handler": lambda m: ("maximize_window", {})},
    {"patterns": [r"\bdesktop\b\s*(?:dikhao|dikha do|dikha|dekhna hai|kholo)", r"\bshow desktop\b"],
     "handler": lambda m: ("show_desktop", {})},
    {"patterns": [r"\b(alt\s?tab|window badlo|switch window|window switch|agle window|next window)\b",
                 r"(\d+)\s*(?:window|windows)\s+(?:badlo|switch|aage)"],
     "handler": lambda m: ("switch_window", {"n": int(m.group(1)) if m.group(1) else 1})},
    {"patterns": [r"\bfocus\b\s+(?:on\s+)?([\w .+-]{2,30})",
                 r"([\w .+-]{2,30}?)\s+(?:pe|par|mein)\s+(?:focus karo|focus|jao|le jao|aa jao)"],
     "handler": lambda m: ("focus_app", {"name": m.group(1).strip()})},
    # Keyboard
    {"patterns": [r"\bclipboard\s*(?:pe|par|mein)?\s*(?:daalo|dalo|rakho|copy)\s+(?P<ct>.+)|"
                 r"\b(?:copy|likh)\s+(?P<ct2>.+?)\s+(?:ko\s+)?clipboard\b"],
     "handler": lambda m: ("clipboard_write", {"text": (m.group("ct") or m.group("ct2")).strip()})},
    {"patterns": [r"^copy$", r"^copy karo$", r"^copy kar do$", r"\bcopy\s*\(?k?ro?\)?$"],
     "handler": lambda m: ("press_key", {"combo": "ctrl+c"})},
    {"patterns": [r"^paste$", r"\bpaste\s*\(?k?ro?\)?$"],
     "handler": lambda m: ("press_key", {"combo": "ctrl+v"})},
    {"patterns": [r"\b(save|undo|redo|select all|find|print|refresh|reload)\b"],
     "handler": lambda m: {
         "save": ("press_key", {"combo": "ctrl+s"}),
         "undo": ("press_key", {"combo": "ctrl+z"}),
         "redo": ("press_key", {"combo": "ctrl+y"}),
         "select all": ("press_key", {"combo": "ctrl+a"}),
         "find": ("press_key", {"combo": "ctrl+f"}),
         "print": ("press_key", {"combo": "ctrl+p"}),
         "refresh": ("press_key", {"combo": "f5"}),
         "reload": ("press_key", {"combo": "f5"}),
     }.get(m.group(1).lower(), ("press_key", {"combo": "ctrl+s"}))},
    {"patterns": [r"\b(?:press|dabao|daba do|daba)\s+(?P<keys>[a-z0-9 +]+)",
                 r"((?:ctrl|control|alt|shift|win|windows)(?:\s*\+\s*\w+)+)\s+(?:dabao|press|karo)"],
     "handler": lambda m: ("press_key", {"combo": m.group("keys") or m.group(1)})},
    {"patterns": [r"\btype\s+(?!karo\b|kar do\b)(?P<t>.+)", r"\b(?:likh do|likhdo)\s+(?P<t2>.+)"],
     "handler": lambda m: ("type_text", {"text": (m.group("t") or m.group("t2")).strip()})},
    {"patterns": [r"\bclipboard\s*(?:pe|par|mein)?\s*(?:padho|read|kya hai|check|dekho)\b", r"\b(copied kya|clipboard)\b\s*$"],
     "handler": lambda m: ("clipboard_read", {})},
    # Mouse
    {"patterns": [r"\bright click\b", r"\bdain click\b"],
     "handler": lambda m: ("mouse_click", {"button": "right"})},
    {"patterns": [r"\bdouble click\b", r"\bdo baar click\b"],
     "handler": lambda m: ("double_click", {})},
    {"patterns": [r"\bclick\b\s*\(?k?ro?\)?\s*"],
     "handler": lambda m: ("mouse_click", {"button": "left"})},
    {"patterns": [r"\bmouse\b.*\bmove\b.*?(\d{1,4})\D+(\d{1,4})", r"\bmove mouse\b.*?(\d{1,4})\D+(\d{1,4})"],
     "handler": lambda m: ("mouse_move", {"x": int(m.group(1)), "y": int(m.group(2))})},
    {"patterns": [r"\bscroll\b.*\b(up|upar|upar ki taraf)\b", r"\b(upar|up)\b\s+scroll\b"],
     "handler": lambda m: ("scroll", {"amount": 3})},
    {"patterns": [r"\bscroll\b.*\b(down|neeche|niche)\b", r"\b(neeche|down)\b\s+scroll\b"],
     "handler": lambda m: ("scroll", {"amount": -3})},
    {"patterns": [r"\bscroll\b\s*(-?\d+)"],
     "handler": lambda m: ("scroll", {"amount": int(m.group(1))})},
    # Brightness
    {"patterns": [r"\b(brightness|brightnes|screen light|roshni|ujala)\b.*\b(\d{1,3})\s*(?:percent|%)?"],
     "handler": lambda m: ("set_brightness", {"percent": min(int(m.group(2)), 100)})},
    {"patterns": [r"\b(brightness|roshni|ujala|screen light)\b.*\b(full|poora|max|100)\b"],
     "handler": lambda m: ("set_brightness", {"percent": 100})},
    {"patterns": [r"\b(brightness|roshni|ujala|screen light)\b.*\b(badhao|badha|zyada|increase|teja|tez)\b"],
     "handler": lambda m: ("brightness_up", {})},
    {"patterns": [r"\b(brightness|roshni|ujala|screen light)\b.*\b(kam|ghatao|decrease|dim|dhundhli)\b"],
     "handler": lambda m: ("brightness_down", {})},
    # System info
    {"patterns": [r"\b(cpu|processor|ram|memory|system|pc|laptop|computer)\b.*\b(kitna|kitni|status|health|usage|chal raha|info|check|speed)\b",
                 r"\b(system info|pc info|cpu usage|ram usage|ram check|cpu check)\b"],
     "handler": lambda m: ("system_info", {})},
    {"patterns": [r"\b(process|processes|task)s?\b.*\b(dikhao|list|kya chal raha|top|kaunse|check)\b"],
     "handler": lambda m: ("list_processes", {"sort_by": "ram" if "ram" in m.group(0).lower() else "cpu"})},
    {"patterns": [r"\bprocess\b.*\b(band|kill|marna|close)\b\s*(?P<p>[\w.\-]+)?",
                 r"\b(band|kill)\b.*\bprocess\b\s*(?P<p2>[\w.\-]+)?"],
     "handler": lambda m: (("kill_process", {"target": m.group("p") or m.group("p2")})
                           if (m.group("p") or m.group("p2")) else
                           ("list_processes", {"sort_by": "cpu"}))},
    {"patterns": [r"\b(pc|computer|laptop|system)\b.*\b(band|shutdown|off)\b"],
     "handler": lambda m: ("shutdown_pc", {"mode": "shutdown"})},
    # Network
    {"patterns": [r"\b(wifi|wi-?fi|network|internet)\b.*\b(kaunsa|kaun sa|naam|kya hai|status|connected|check)\b",
                 r"\bip\b.*\b(address|kya|batao|check)?\b"],
     "handler": lambda m: ("network_info", {})},
    # Files
    {"patterns": [r"\b(file|folder|document|photo|video file)\b.*\b(dhund|search|find|khoj)\w*\b\s+(?P<f>.+)",
                 r"\b(?:dhundo|dhundho|khojo|find)\b\s+(?P<f2>.+?)\s+(?:file|folder|naam ka file)\b"],
     "handler": lambda m: ("search_files", {"name": (m.group("f") or m.group("f2")).strip().strip("\"'")})},
    {"patterns": [r"\b(?:folder|directory)\s+(?:banao|banado|create)\s+(?P<fp>.+)|\b(?:banao|create)\s+(?:folder|directory)\s+(?P<fp2>.+)"],
     "handler": lambda m: ("create_folder", {"path": (m.group("fp") or m.group("fp2")).strip().strip("\"'")})},
    {"patterns": [r"\b(?:folder)\s+(?:kholo|open|khol do)\s+(?P<op>.+)|\b(?:kholo|open)\s+(?:folder)\s+(?P<op2>.+)"],
     "handler": lambda m: ("open_folder", {"path": (m.group("op") or m.group("op2")).strip().strip("\"'")})},
    {"patterns": [r"\b(recycle ?bin|trash|kachra ?dan)\b.*\b(khali|empty|clean|saaf)\b"],
     "handler": lambda m: ("empty_recycle_bin", {})},
    # Close app
    {"patterns": [r"^(?P<close_app_name>[\w .\-]{2,25}?)\s+(?:ko\s+)?(?:band|bond)\s+k?ro?$",
                 r"\b(?:band|close)\s+k?ro?\b\s+(?P<close_app_name2>[\w .\-]{2,25})$"],
     "handler": lambda m: ("close_app", {"name": (m.group("close_app_name") or m.group("close_app_name2")).strip()})},
    # YouTube
    {"patterns": [r"\b(youtube|yt)\b.*\b(search|dhundo|khojo)\b\s+(.+)", r"\b(search|dhundo)\b.*\b(youtube|yt)\b\s+(.+)"],
     "handler": lambda m: ("youtube_search", {"query": m.group(m.lastindex) if m.lastindex else m.group(0)})},
    {"patterns": [
        r"\b(youtube|yt|video|gaana)\b\s*(?:per|pe|par|on)?\s*(?P<q>.+?)\s*\b(play|chalao|laga|chala|sunao)\b",
        r"\b(play|chalao|laga)\b\s+(?P<q>.+?)\s*\b(on youtube|pe youtube|yt par|yt pe)\b",
    ],
     "handler": lambda m: ("youtube_play_video", {"query_or_id": m.group("q").strip()})},
    {"patterns": [r"\b(mere|apne)\b.*\b(youtube|video)s?\b.*\b(dikhao|list|kya hai)\b", r"\b(my|channel)\b.*\b(videos?)\b"],
     "handler": lambda m: ("youtube_get_my_videos", {"max_results": 10})},
    {"patterns": [r"\b(youtube|yt)\b.*\b(auth|login|status|check)\b"],
     "handler": lambda m: ("youtube_check_auth", {})},
# Volume (existing simple rules)
    {"patterns": [r"\b(volume|aawaz|sound)\b.*\b(\d+)\b"],
     "handler": lambda m: ("set_volume", {"percent": int(m.group(2))})},
    {"patterns": [r"\b(volume|aawaz)\b.*\b(badhao|up|badha|increase)\b"],
     "handler": lambda m: ("change_volume", {"delta": 10})},
    {"patterns": [r"\b(volume|aawaz)\b.*\b(kam|down|ghatao|decrease)\b"],
     "handler": lambda m: ("change_volume", {"delta": -10})},
    {"patterns": [r"\b(mute|chup|khamosh)\b"],
     "handler": lambda m: ("toggle_mute", {"mute": True})},
    {"patterns": [r"\b(unmute)\b|\b(awaaz)\b.*\b(de|do|on)\b"],
     "handler": lambda m: ("toggle_mute", {"mute": False})},

    # Weather
    {"patterns": [r"\b(mausam|weather|taapmaan|temperature)\b.*\b(kaisa|kya|batao|check)\b",
                 r"\b(aaj|today)\b.*\b(mausam|weather)\b"],
     "handler": lambda m: ("get_weather", {"city": "Delhi"})},
    {"patterns": [r"\b(mausam|weather)\b\s+(?P<city>[\w\s]{2,30})"],
     "handler": lambda m: ("get_weather", {"city": m.group("city").strip()})},

    # Date/Time (use get_time with kind)
    {"patterns": [r"\b(date|tareekh|aaj.*date)\b", r"\b(aaj|today)\b.*\b(kaun.*saal|kaun.*mahina|kaun.*din)\b"],
     "handler": lambda m: ("get_time", {"kind": "date"})},
    {"patterns": [r"\b(time|samay|waqt)\b.*\b(kya|kitna|batao)\b", r"\b(abhi|right now)\b.*\b(time|samay)\b"],
     "handler": lambda m: ("get_time", {"kind": "time"})},

    # Web search / Wikipedia
    {"patterns": [r"\b(google|search|dhundho|khojo)\b\s+(?P<q>.+)",
                 r"\b(?:google|web|internet)\b.*\b(?:search|dhundho|khojo)\b\s+(?P<q>.+)"],
     "handler": lambda m: ("web_search", {"query": (m.group("q") or "").strip()})},
    {"patterns": [r"\b(wikipedia|wiki)\b\s+(?P<q>.+?)(?:\s+(?:se|ke|baare|mein|batao|padho|search|about|on))\b",
                 r"\b(wikipedia|wiki)\b\s+(?P<q>.+)"],
     "handler": lambda m: ("wikipedia_summary", {"topic": (m.group("q") or "").strip()})},

    # Open apps
    {"patterns": [r"\b(open|kholo|chalao)\b\s+(?P<app>notepad|calculator|calc|cmd|command prompt|powershell|terminal|explorer|file explorer|browser|chrome|edge|firefox|vscode|code|word|excel|powerpoint|paint|photos|calendar|mail|task manager|taskmgr)\b",
                 r"\b(?P<app>notepad|calculator|calc|cmd|command prompt|powershell|terminal|explorer|file explorer|browser|chrome|edge|firefox|vscode|code|word|excel|powerpoint|paint|photos|calendar|mail|task manager|taskmgr)\b\s+(?:kholo|open|chalao)"],
     "handler": lambda m: ("open_app", {"name": (m.group("app") or "").strip()})},

    # Screenshot
    {"patterns": [r"\b(screenshot|screen shot|screen capture|print screen)\b.*\b(lo|le|karo|do)\b",
                 r"\b(lo|le|karo)\b.*\b(screenshot|screen shot)\b"],
     "handler": lambda m: ("take_screenshot", {})},

    # System power (restart via shutdown_pc mode) - require explicit confirmation
    {"patterns": [r"\b(pc|computer|laptop|system)\b.*\b(restart|reboot|dobara chalao)\b.*\b(confirm|pukka|haan|sure|sure karo)\b",
                 r"\b(restart|reboot)\b.*\b(karo|do)\b.*\b(confirm|pukka|haan|sure)\b"],
     "handler": lambda m: ("shutdown_pc", {"mode": "restart"})},
    {"patterns": [r"\b(pc|computer|laptop|system)\b.*\b(shutdown|band|off)\b.*\b(confirm|pukka|haan|sure|sure karo)\b",
                 r"\b(shutdown|band karo)\b.*\b(confirm|pukka|haan|sure)\b"],
     "handler": lambda m: ("shutdown_pc", {"mode": "shutdown"})},
    # Without confirmation - just inform
    {"patterns": [r"\b(pc|computer|laptop|system)\b.*\b(restart|reboot|dobara chalao)\b",
                 r"\b(restart|reboot)\b.*\b(karo|do)\b"],
     "handler": lambda m: "PC restart karne ke liye 'confirm' ya 'pukka' bolo."},
    {"patterns": [r"\b(pc|computer|laptop|system)\b.*\b(shutdown|band|off)\b",
                 r"\b(shutdown|band karo)\b"],
     "handler": lambda m: "PC shutdown karne ke liye 'confirm' ya 'pukka' bolo."},

    # Lock PC
    {"patterns": [r"\b(lock|lock screen|screen lock|pc lock)\b"],
     "handler": lambda m: ("lock_pc", {})},

    # Battery (laptop)
    {"patterns": [r"\b(battery|batteri|charge)\b.*\b(kitna|kya|status|check|percentage)\b",
                 r"\b(battery|batteri)\b.*\b(bacha|remaining|kitna bacha)\b"],
     "handler": lambda m: ("battery_status", {})},

    # Keyboard shortcuts
    {"patterns": [r"\b(win|windows)\s*[\+\-]\s*d\b", r"\b(show desktop|desktop dikhao)\b"],
     "handler": lambda m: ("press_key", {"combo": "win+d"})},
    {"patterns": [r"\b(win|windows)\s*[\+\-]\s*e\b", r"\b(open explorer|file explorer kholo)\b"],
     "handler": lambda m: ("press_key", {"combo": "win+e"})},
    {"patterns": [r"\b(win|windows)\s*[\+\-]\s*r\b", r"\b(run dialog|run kholo)\b"],
     "handler": lambda m: ("press_key", {"combo": "win+r"})},
    {"patterns": [r"\b(win|windows)\s*[\+\-]\s*l\b", r"\b(lock|lock screen|screen lock)\b"],
     "handler": lambda m: ("press_key", {"combo": "win+l"})},
    {"patterns": [r"\b(alt\s*[\+\-]\s*tab|window switch|window badlo)\b"],
     "handler": lambda m: ("press_key", {"combo": "alt+tab"})},
    {"patterns": [r"\b(ctrl\s*[\+\-]\s*shift\s*[\+\-]\s*esc|task manager|taskmgr)\b"],
     "handler": lambda m: ("press_key", {"combo": "ctrl+shift+esc"})},
    {"patterns": [r"\b(win|windows)\s*[\+\-]\s*i\b", r"\b(settings|setting)\b\s*(?:kholo|open)\b"],
     "handler": lambda m: ("press_key", {"combo": "win+i"})},

    # Empty recycle bin (already there but adding more patterns)
    {"patterns": [r"\b(kachra|trash|recycle)\s*(?:bin|dan)\s*(?:khali|empty|saaf)\b",
                 r"\b(khali|empty|saaf)\b.*\b(kachra|trash|recycle)\b"],
     "handler": lambda m: ("empty_recycle_bin", {})},
]


def _try_rules(text):
    t = text.lower().strip()
    tl = t.strip()
    if any(g in tl for g in _greetings_hi):
        return "Namaste! Haan boliye, kya kaam hai?"
    if any(g in tl for g in _greetings_en):
        return "Hello! What can I do for you?"
    if tl in ("jarvis", "hey jarvis"):
        return "Haan boliye!"
    for rule in RULES:
        for pat in rule["patterns"]:
            m = re.search(pat, t)
            if not m:
                continue
            result = rule["handler"](m)
            if isinstance(result, str):
                return result
            if isinstance(result, tuple) and result[0] == "__time__":
                return _time_response(_detect_lang(t)) if "date" in t or "tareekh" in t else _time_response(_detect_lang(t))
            name, args = result
            return str(execute(name, args))
    return None


class JarvisAgent:
    def __init__(self):
        self.history = deque(maxlen=HISTORY_MAX)
        self._schemas = get_schemas()
        self.context = {"topic": None, "entities": {}, "pending_command": None}
        self._tts_player = None

    def set_tts_player(self, tts_player):
        self._tts_player = tts_player

    def update_context(self, user_text, lang):
        t = user_text.lower().strip()
        if lang == "hi":
            for phrase, meaning in [
                ("youtube", "youtube"), ("google", "web_search"), ("wikipedia", "wikipedia_summary"),
                ("weather", "get_weather"), ("time", "time"), ("date", "date"), ("volume", "volume"),
                ("brightness", "brightness"), ("system", "system_info"), ("process", "list_processes"),
                ("file", "search_files"), ("folder", "create_folder"), ("clipboard", "clipboard_read"),
                ("recycle", "empty_recycle_bin"),
            ]:
                if phrase in t:
                    self.context["topic"] = meaning
                    break
        else:
            for phrase, meaning in [
                ("youtube", "youtube"), ("google", "web_search"), ("wikipedia", "wikipedia_summary"),
                ("weather", "get_weather"), ("time", "time"), ("date", "date"), ("volume", "volume"),
                ("brightness", "brightness"), ("system", "system_info"), ("process", "list_processes"),
                ("file", "search_files"), ("folder", "create_folder"), ("clipboard", "clipboard_read"),
                ("recycle", "empty_recycle_bin"),
            ]:
                if phrase in t:
                    self.context["topic"] = meaning
                    break
        words = [w for w in t.split() if w not in {"kaise", "kya", "hai", "ho", "main", "mujhe"}]
        if words:
            self.context["entities"] = {"last_keyword": words[0]}

    def get_context_snippet(self):
        if self.context.get("topic"):
            topic_map = {
                "youtube": "YouTube video", "web_search": "web search",
                "wikipedia_summary": "Wikipedia article", "get_weather": "weather",
                "time": "current time", "volume": "volume control",
                "brightness": "screen brightness", "system_info": "system information",
                "list_processes": "process list", "search_files": "file search",
                "create_folder": "folder creation", "clipboard_read": "clipboard readout",
                "empty_recycle_bin": "recycle bin empty",
            }
            topic = topic_map.get(self.context["topic"], "PC action")
            return f"Context: User is interested in {topic}. "
        return ""

    def add_to_history(self, user_text, response, emotion="neutral"):
        entry = {"user": user_text, "jarvis": response, "emotion": emotion}
        self.history.append(entry)

    def get_recent_context(self, n=3):
        recents = list(self.history)[-n:]
        lines = []
        for entry in recents:
            lines.append(f"User: {entry['user']}")
            lines.append(f"Jarvis: {entry['jarvis']}")
        return "\n".join(lines)

    async def handle(self, user_text, lang=None):
        """Async handle with interruption support."""
        user_text = user_text.strip()
        if not user_text:
            return "", "neutral"
        if lang is None:
            lang = _detect_lang(user_text)

        # Update conversation context
        self.update_context(user_text, lang)

        # Fast rule-based path
        fast = _try_rules(user_text)
        if fast:
            if isinstance(fast, tuple) and len(fast) == 2:
                resp, emotion = fast
                self.add_to_history(user_text, resp, emotion)
                return resp, emotion
            resp = fast
            self.add_to_history(user_text, resp, "neutral")
            return resp, "neutral"

        # LLM path with context
        context_snippet = self.get_context_snippet()
        system_prompt = SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS["hi"])
        if context_snippet:
            system_prompt = context_snippet + system_prompt

        self.history.append({"role": "user", "content": user_text})
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(list(self.history))

        final_text = ""
        for _ in range(3):
            resp, backend = llm.chat(messages, tools=None)
            if resp["tool_calls"]:
                for tc in resp["tool_calls"]:
                    result = execute(tc["name"], tc["args"])
                    final_text = str(result)
                break
            final_text = resp["content"]
            break

        if not final_text:
            fallback = "Sorry, I didn't get that. Please try again." if lang == "en" else "Samajh nahi aaya, dubara boliye."
            final_text = fallback

        # Enforce short responses
        final_text = _truncate_response(final_text, lang, max_lines=2)

        self.history.append({"role": "assistant", "content": final_text})
        emotion = _detect_emotion_from_text(final_text)
        self.add_to_history(user_text, final_text, emotion)
        return final_text, emotion

    def interrupt(self):
        """Called when user interrupts - abort any ongoing TTS."""
        pass  # TTS player handles its own abort


# Backward compatibility
JarvisAgent._try_rules = staticmethod(_try_rules)
JarvisAgent._detect_lang = staticmethod(_detect_lang)


if __name__ == "__main__":
    agent = JarvisAgent()
    print("Jarvis text mode (type 'quit' to exit)")
    while True:
        user = input("Aap: ").strip()
        if user.lower() in ("quit", "exit", "q", "bye"):
            break
        resp = agent.handle(user)
        print(f"Jarvis: {resp}")