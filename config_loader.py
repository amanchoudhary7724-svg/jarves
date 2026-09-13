import json
import os
import logging
import sys

log = logging.getLogger(__name__)


def _resolve_env_placeholders(obj, parent_key=""):
    """Recursively replace __ENV:VAR_NAME__ placeholders with os.environ values."""
    if isinstance(obj, str):
        if obj.startswith("__ENV:") and obj.endswith("__"):
            var_name = obj[6:-2]
            val = os.environ.get(var_name, "")
            if not val:
                log.debug("Environment variable %s not set (referenced in config.%s)", var_name, parent_key)
            return val
        return obj
    if isinstance(obj, dict):
        return {k: _resolve_env_placeholders(v, f"{parent_key}.{k}" if parent_key else k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_env_placeholders(item, parent_key) for item in obj]
    return obj


def _load_env_file():
    """Load .env file if it exists (simple key=value, no complex parsing)."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def _load():
    _load_env_file()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return _resolve_env_placeholders(cfg)


CFG = _load()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def open_browser(url, timeout=5):
    """Open a URL in the default browser. Non-blocking and never inherits
    our stdio handles (so it can't hang a piped parent process)."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(url)
        else:
            import subprocess
            subprocess.Popen(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                close_fds=True,
            )
    except Exception:
        pass
    return True
