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
    return bool(CFG.get("nvidia_api_key"))


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


def _try_local(messages, tools):
    model = CFG["models"]["local_backup"]
    tool_list = []
    if tools:
        for t in tools:
            fn = t.get("function", {})
            desc = fn.get("description", "")
            params = fn.get("properties", {})
            tool_list.append(f"- {fn.get('name', '?')}: {desc}")
    tool_section = ""
    if tool_list:
        tool_section = "\n\nAvailable tools:\n" + "\n".join(tool_list)
    local_messages = list(messages)
    if tool_list:
        tool_format = """You can call tools by writing EXACTLY this format (no other format):
<tool_call name="tool_name">{"param": "value"}</tool_call>

You can call multiple tools in one response."""
        if local_messages and local_messages[0]["role"] == "system":
            local_messages[0] = {
                "role": "system",
                "content": local_messages[0]["content"] + tool_section + "\n\n" + tool_format,
            }
        else:
            local_messages.insert(0, {
                "role": "system",
                "content": "You are Jarvis." + tool_section + "\n\n" + tool_format,
            })
    try:
        resp = ollama.chat(model=model, messages=local_messages)
        content = (resp.message.content or "").strip()
        if tool_list:
            tool_calls, cleaned = _parse_tool_calls_from_text(content)
            return {"content": cleaned, "tool_calls": tool_calls}
        return {"content": content, "tool_calls": []}
    except Exception as e:
        print(f"[LLM] Ollama fail: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print("Internet:", has_internet())
    print("NVIDIA key:", "hai" if nvidia_ready() else "nahi (config.json bharo)")
    out, backend = chat([{"role": "user", "content": "Namaste, aap kaun ho?"}])
    print(f"[{backend}] {out['content'][:200]}")
