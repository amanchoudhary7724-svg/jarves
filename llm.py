import json
import re
import socket

import ollama
from openai import OpenAI

from config_loader import CFG

COMPLEX_KEYWORDS = [
    "code", "coding", "program", "script", "likho", "likh do", "essay",
    "nibandh", "math", "ganit", "solve", "samjhao", "explain", "detail",
    "algorithm", "function", "project", "kahani", "story", "email likho",
    "letter", "analysis", "compare", "tulna", "kaise banaye", "tutorial",
    "translate", "anuvad",
]

_client = None


def _nvidia_client():
    global _client
    if _client is None and nvidia_ready():
        _client = OpenAI(
            base_url=CFG.get("nvidia_base_url"),
            api_key=CFG["nvidia_api_key"],
            timeout=90,
            max_retries=0,
        )
    return _client


def nvidia_ready():
    key = CFG.get("nvidia_api_key", "")
    # Reject placeholder / empty keys
    if not key or key.startswith("__ENV:") or key == "__ENV:NVIDIA_API_KEY__":
        return False
    return True


def has_internet(timeout=2.0):
    try:
        socket.create_connection(("integrate.api.nvidia.com", 443), timeout=timeout)
        return True
    except OSError:
        return False


def is_complex(text):
    t = text.lower()
    if any(k in t for k in COMPLEX_KEYWORDS):
        return True
    return len(t) > 140


_TIERS = {"fast": "cloud_fast", "mid": "cloud_mid", "heavy": "cloud_heavy"}

_HEAVY_KEYWORDS = [
    "optimize", "optimise", "behter", "sudhar", "analysis", "analyze", "analyse",
    "compare", "tulna", "architecture", "design", "refactor", "research",
    "full report", "poora report", "improve", "kaise banaye", "tutorial",
    "algorithm", "complex", "brainstorm", "strategy", "deep", "reason",
    "debug", "fix", "root cause", "why",
]

_MID_KEYWORDS = [
    "code", "coding", "program", "script", "likho", "likh do", "project",
    "banao", "create", "website", "game", "app", "android", "email likho",
    "letter", "translate", "story", "kahani", "math", "ganit", "solve",
    "samjhao", "explain", "essay", "nibandh", "summary", "anuvad",
]


def _select_tier(text):
    t = text.lower()
    if any(k in t for k in _HEAVY_KEYWORDS):
        return "heavy"
    if any(k in t for k in _MID_KEYWORDS) or len(t) > 140:
        return "mid"
    return "fast"


def _safe_json(s):
    if isinstance(s, dict):
        return s
    try:
        return json.loads(s) if s else {}
    except Exception:
        return {}


def _extract_openai(resp):
    msg = resp.choices[0].message
    tool_calls = []
    for tc in getattr(msg, "tool_calls", None) or []:
        if isinstance(tc, dict):
            fn = tc.get("function", {})
            name = fn.get("name", "") if isinstance(fn, dict) else getattr(fn, "name", "")
            args = fn.get("arguments", {}) if isinstance(fn, dict) else getattr(fn, "arguments", "{}")
        else:
            fn = tc.function
            name = fn.name
            args = fn.arguments
        tool_calls.append({"name": name, "args": _safe_json(args)})
    content = getattr(msg, "content", None) or ""
    return {"content": content.strip(), "tool_calls": tool_calls}


def _parse_tool_calls_from_text(text):
    tool_calls = []
    patterns = [
        r'<tool_call name="(\w+)">\s*(.*?)\s*</tool_call>',
        r'<tool_call name="(\w+)">(.*?)</tool_call>',
        r'```tool_call\nname: (\w+)\nargs: ({.*?})\n```',
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.DOTALL):
            name = m.group(1)
            args_str = m.group(2).strip()
            try:
                args = json.loads(args_str) if args_str.startswith("{") else {}
            except Exception:
                args = {}
            tool_calls.append({"name": name, "args": args})
    cleaned = text
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return tool_calls, cleaned


def _candidates(primary):
    pool = CFG.get("model_pool") or []
    seq = [primary]
    for m in pool:
        if m not in seq:
            seq.append(m)
    return seq


def _is_rate_limit(err):
    s = str(err).lower()
    return any(k in s for k in ("rate", "limit", "quota", "429", "too many", "exceeded", "capacity"))


def chat(messages, tools=None, force_local=False, tier=None):
    models = CFG["models"]
    if force_local or not (nvidia_ready() and has_internet()):
        result = _try_local(messages, tools)
        if result is not None:
            return result, f"local:{models['local_backup']}"
        return {
            "content": "Sorry sir, main abhi server se connect nahi kar paya. Thodi der baad try karein.",
            "tool_calls": [],
        }, "none"

    last_user = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )
    sel = tier if tier in _TIERS else _select_tier(str(last_user))
    primary = models[_TIERS[sel]]

    for model in _candidates(primary):
        result = _try_nvidia(model, messages, tools)
        if result is not None:
            return result, f"cloud:{model}"
    # sab cloud fail -> local
    result = _try_local(messages, tools)
    if result is not None:
        return result, f"local:{models['local_backup']}"
    return {
        "content": "Sorry sir, main abhi server se connect nahi kar paya. Thodi der baad try karein.",
        "tool_calls": [],
    }, "none"


def _try_nvidia(model, messages, tools):
    client = _nvidia_client()
    if client is None:
        return None
    kwargs = dict(model=model, messages=messages, temperature=0.6, max_tokens=4096)
    if tools:
        kwargs["tools"] = tools
    try:
        resp = client.chat.completions.create(**kwargs)
        return _extract_openai(resp)
    except Exception as e:
        if _is_rate_limit(e):
            print(f"[LLM] {model} limit/quota hit -> agla model try kar raha hoon...")
        else:
            print(f"[LLM] {model} fail ({type(e).__name__}) -> agla model...")
        return None


def _extract_ollama(resp):
    """Extract content and tool_calls from Ollama ChatResponse."""
    msg = resp.message
    content = (msg.content or "").strip()
    tool_calls = []
    for tc in getattr(msg, "tool_calls", None) or []:
        if hasattr(tc, "function"):
            fn = tc.function
            name = getattr(fn, "name", "")
            args = getattr(fn, "arguments", {})
            if isinstance(args, str):
                args = _safe_json(args)
            tool_calls.append({"name": name, "args": args})
        elif isinstance(tc, dict):
            fn = tc.get("function", {})
            name = fn.get("name", "") if isinstance(fn, dict) else ""
            args = fn.get("arguments", {}) if isinstance(fn, dict) else {}
            if isinstance(args, str):
                args = _safe_json(args)
            tool_calls.append({"name": name, "args": args})
    return {"content": content, "tool_calls": tool_calls}


def _filter_tools_for_query(tools, user_text):
    """Return a subset of tools relevant to the user's query (reduces prompt
    size for small local models). Falls back to all tools if no match."""
    if not tools:
        return tools
    t = user_text.lower()
    # Keyword -> tool name prefix mapping for common intents
    keyword_map = {
        "open|kholo|chalao|launch|start": ["open_app"],
        "close|band|shutdown|shut": ["close_app"],
        "volume|awaz|aawaz|sound|speaker": ["set_volume", "change_volume", "get_volume"],
        "brightness|roshni|screen": ["set_brightness", "change_brightness"],
        "play|chalo|chalaao|song|music|video": ["youtube_play_video", "youtube_search", "play_media", "pause_media"],
        "youtube|search|dhoondh|khoj": ["youtube_search", "web_search"],
        "screenshot|screen capture|screen shot": ["take_screenshot"],
        "time|waqt|samay|kitne baje": ["get_time"],
        "date|tarikh|aaj|kal": ["get_time"],
        "battery|charge|power": ["battery_status"],
        "wifi|internet|network|connection": ["network_info", "diagnose_network", "wifi_diagnostics", "wifi_password", "check_local_ports", "ping_test", "ip_config"],
        "bluetooth|bt": ["bluetooth_toggle"],
        "email|mail|bhejo|pathao": ["send_email", "check_email"],
        "calendar|meeting|event|schedule": ["list_calendar_events"],
        "file|folder|directory|path": ["open_folder", "list_files", "file_info", "read_file", "write_file", "edit_file"],
        "process|task manager|running": ["list_processes", "kill_process"],
        "system|pc|computer|specs|info": ["system_info", "shutdown_pc", "empty_recycle_bin"],
        "port|ports|ping|ipconfig|diagnose|diagnosis": ["diagnose_network", "check_local_ports", "ping_test", "ip_config", "wifi_diagnostics"],
        "keyboard|type|likh do| likho": ["type_text", "press_key"],
        "mouse|click|cursor": ["mouse_click"],
        "clipboard|copy|paste|paste_from": ["get_clipboard", "set_clipboard"],
        "weather|mausam|tapman": ["get_weather"],
        "notify|notification|alert": ["send_notification"],
        "reminder|yaad dila": ["set_reminder"],
        "command|cmd|run|execute|terminal|powershell": ["run_command"],
        "joke|hasi|mazaak": [],
        "who|kaun|name|naam": [],
    }
    matched = set()
    for keywords, tool_names in keyword_map.items():
        if any(k in t for k in keywords.split("|")):
            matched.update(tool_names)
    if not matched:
        return tools  # no keyword match -> send all
    # Always include the most generic tools
    always = {"open_app", "close_app", "web_search", "get_time", "battery_status"}
    matched.update(always)
    return [tool for tool in tools if tool.get("function", {}).get("name", "") in matched]


_LOCAL_MAX_TOOLS = 30  # qwen2.5:1.5b hangs with >30 tools


def _try_local(messages, tools):
    model = CFG["models"]["local_backup"]
    tools = tools or []
    # Get user text for tool filtering
    user_text = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_text = m.get("content", "")
            break
    filtered = _filter_tools_for_query(tools, user_text)
    # Cap at 30 tools — small models hang with too many
    if len(filtered) > _LOCAL_MAX_TOOLS:
        filtered = filtered[:_LOCAL_MAX_TOOLS]
    local_messages = list(messages)
    try:
        kwargs = dict(model=model, messages=local_messages)
        if filtered:
            kwargs["tools"] = filtered
        resp = ollama.chat(**kwargs)
        # Check if Ollama returned tool calls natively
        if resp.message.tool_calls:
            return _extract_ollama(resp)
        content = (resp.message.content or "").strip()
        return {"content": content, "tool_calls": []}
    except Exception as e:
        print(f"[LLM] Ollama fail: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print("Internet:", has_internet())
    print("NVIDIA key:", "hai" if nvidia_ready() else "nahi (config.json bharo)")
    out, backend = chat([{"role": "user", "content": "Namaste, aap kaun ho?"}])
    print(f"[{backend}] {out['content'][:200]}")
