import os
import re
import sys
import json
import subprocess
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_loader import CFG

log = logging.getLogger(__name__)

AUTO = CFG.get("developer", {}).get("allow_command_exec", False)
WRITE = CFG.get("developer", {}).get("allow_file_write", True)
ALLOWED_WRITE_ROOTS = CFG.get("developer", {}).get(
    "allowed_write_roots",
    [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "builds")],
)

# Dangerous command patterns - any match rejects execution
_BLOCKED_PATTERNS = re.compile(
    r"""
    (?:
        \bdel\s+/[sqaf]\b|
        \bformat\s+[a-z]:|
        \brd\s+/s\b|\brmdir\s+/s\b|
        \bnet\s+user\b|\bnet\s+localgroup\b|
        \breg\s+(?:delete|add)\b|
        \bmklink\b|\battrib\s+\b|\bicacls\b|
        \btakeown\b|\bsecedit\b|
        \bshutdown\s+/[srf]\b|
        \btaskkill\s+/[fim]\b.*(?:system|svchost|csrss|lsass|winlogon|explorer|services|dwm)\b|
        \b(wget|curl)\b.*\|\s*\b(?:sh|bash|cmd|powershell)\b|
        \bInvoke-Expression\b|\bStart-Process\b.*-Verb\s+runAs|
        -\s*".*"\s*-\s*".*"\s*;|
        \bpython\s+-c\s+.*(?:import\s+os|import\s+subprocess|shutil\.rmtree|os\.remove)
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Shell metacharacters that enable chaining
_SHELL_META = re.compile(r'[|&;<>]')


def _is_path_allowed(path: str) -> bool:
    """Check if the resolved absolute path falls under an allowed write root."""
    try:
        resolved = os.path.realpath(os.path.abspath(path))
    except (OSError, ValueError):
        return False
    return any(
        resolved.lower().startswith(os.path.realpath(os.path.abspath(root)).lower() + os.sep)
        or resolved.lower() == os.path.realpath(os.path.abspath(root)).lower()
        for root in ALLOWED_WRITE_ROOTS
    )


def _ok():
    return "developer mode enabled" if CFG.get("developer", {}).get("enabled", True) else "developer mode disabled in config"


def read_file(path, max_lines=2000):
    if not os.path.exists(path):
        return f"File nahi hai: {path}"
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            head = "".join(lines[:max_lines // 2])
            tail = "".join(lines[-max_lines // 2:])
            return f"{head}\n... [{len(lines) - max_lines} lines cut] ...\n{tail}"
        return "".join(lines)
    except Exception as e:
        return f"Read error: {type(e).__name__}: {e}"


def write_file(path, content):
    if not WRITE:
        return "File write disabled in config."
    if not _is_path_allowed(path):
        return f"BLOCKED: Path '{path}' allowed write roots ke bahar hai. Sirf builds folder mein likh sakte ho."
    try:
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        size = os.path.getsize(path)
        log.info("File written: %s (%d bytes)", path, size)
        return f"File likh diya: {path} ({size} bytes)"
    except Exception as e:
        return f"Write error: {type(e).__name__}: {e}"


def edit_file(path, old_str, new_str):
    if not WRITE:
        return "File write disabled in config."
    if not _is_path_allowed(path):
        return f"BLOCKED: Path '{path}' allowed write roots ke bahar hai. Sirf builds folder mein edit kar sakte ho."
    if not os.path.exists(path):
        return f"File nahi hai: {path}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        if old_str not in text:
            return f"'{old_str[:40]}...' file mein nahi mila. Exact match chahiye."
        count = text.count(old_str)
        new_text = text.replace(old_str, new_str)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_text)
        log.info("File edited: %s (%d replacements)", path, count)
        return f"Edit ho gaya: {path} ({count} jagah badla)"
    except Exception as e:
        return f"Edit error: {type(e).__name__}: {e}"


def list_files(path="."):
    if not os.path.exists(path):
        return f"Path nahi hai: {path}"
    try:
        items = []
        for root, dirs, files in os.walk(path):
            depth = root[len(path):].count(os.sep)
            if depth > 2:
                dirs[:] = []
                continue
            indent = "  " * depth
            items.append(f"{indent}{os.path.basename(root)}/")
            for f in sorted(files)[:50]:
                items.append(f"{indent}  {f}")
        return "\n".join(items[:200]) if items else "Empty folder"
    except Exception as e:
        return f"List error: {type(e).__name__}: {e}"


def run_command(command, timeout=120):
    if not AUTO:
        return "Command exec disabled in config."
    if not command or not command.strip():
        return "Command khali hai."
    command = command.strip()
    # Check dangerous patterns
    if _BLOCKED_PATTERNS.search(command):
        log.warning("Blocked dangerous command: %s", command[:200])
        return "BLOCKED: Yeh command dangerous hai aur execute nahi hoga. Jarvis security rules ke under blocked."
    # Check shell metacharacters (pipe, chain, redirect)
    if _SHELL_META.search(command):
        log.warning("Blocked command with shell metacharacters: %s", command[:200])
        return "BLOCKED: Shell metacharacters (|, &, ;, >, <) allowed nahi hain. Single command do."
    log.info("Executing command: %s", command[:200])
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=CFG.get("developer", {}).get("workspace", "."),
        )
        out = result.stdout or ""
        err = result.stderr or ""
        combined = (out + "\n" + err).strip()
        if not combined:
            combined = f"[Command finished, exit code {result.returncode}, no output]"
        if len(combined) > 4000:
            combined = combined[:4000] + "\n... [output truncated]"
        return combined
    except subprocess.TimeoutExpired:
        return f"Command timeout ({timeout}s) cross kar gaya."
    except Exception as e:
        return f"Command error: {type(e).__name__}: {e}"


def create_project(name, structure_json, base_path=None):
    if not WRITE:
        return "File write disabled in config."
    if base_path is None:
        base_path = CFG.get("project_builder", {}).get(
            "output_root", "C:/Users/soura/Documents/Default Project/jarvis/builds"
        )
    try:
        if isinstance(structure_json, str):
            structure = json.loads(structure_json)
        else:
            structure = structure_json
        root = os.path.join(base_path, name)
        os.makedirs(root, exist_ok=True)
        written = []
        for rel, content in structure.items():
            fp = os.path.join(root, rel)
            os.makedirs(os.path.dirname(os.path.abspath(fp)), exist_ok=True)
            with open(fp, "w", encoding="utf-8") as f:
                f.write(content if isinstance(content, str) else json.dumps(content, indent=2))
            written.append(rel)
        log.info("Project created: %s (%d files)", root, len(written))
        return f"Project '{name}' ban gaya: {root}\nFiles: {', '.join(written)}"
    except json.JSONDecodeError as e:
        return f"Structure JSON galat hai: {e}"
    except Exception as e:
        return f"Create error: {type(e).__name__}: {e}"


def _llm(prompt, system, tier="cloud_mid"):
    try:
        import llm
        resp, _ = llm.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ], tools=None, tier=tier)
        return resp.get("content", "")
    except Exception as e:
        return f"LLM error: {type(e).__name__}: {e}"


def explain_code(path, language="auto"):
    code = read_file(path)
    if code.startswith("File nahi") or code.startswith("Read error"):
        return code
    prompt = f"Is code ko simple Hindi/English mein samjhao. File: {os.path.basename(path)}\n\n```\n{code[:6000]}\n```"
    return _llm(prompt, "Tum ek expert programmer ho. Code clear aur simple samjhao, Hinglish mein.", tier="cloud_mid")


def debug_code(path, error_msg=""):
    code = read_file(path)
    if code.startswith("File nahi") or code.startswith("Read error"):
        return code
    prompt = f"Is code mein error hai. Fix karo aur sirf fixed code return karo (explanation kam do).\n\nERROR:\n{error_msg}\n\nCODE:\n```\n{code[:6000]}\n```"
    fixed = _llm(prompt, "Tum expert debugger ho. Bug fix karo, fixed code do.", tier="cloud_heavy")
    if fixed and CFG.get("developer", {}).get("confirm_destructive", True):
        return f"Debug analysis (auto-write disabled, confirm_destructive=true):\n{fixed[:2000]}\n\nFile manually save karni hogi."
    if fixed and (WRITE or CFG.get("developer", {}).get("allow_file_write", True)):
        edit_or_write = write_file(path, fixed)
        return f"Debug ho gaya. {edit_or_write}\n\n--- Fixed code preview ---\n{fixed[:500]}"
    return f"Debug analysis:\n{fixed}"


def generate_code(description, language="python"):
    prompt = f"Ek complete, working {language} program banao is description ke liye: {description}\n\nSirf code do, comments ke saath. Agar multiple files hain toh har file '=== filename ===' se start karo."
    code = _llm(prompt, f"Tum expert {language} developer ho. Production-quality code likho.", tier="cloud_mid")
    return f"Generated {language} code:\n\n{code}"


if __name__ == "__main__":
    print(read_file(__file__, 5))
    print(write_file(os.path.join(os.environ["TEMP"], "jarvis_test.txt"), "hello"))
    print(list_files(".")[:300])

