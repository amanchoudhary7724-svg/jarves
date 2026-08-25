import os
import sys
import json
import re
import shutil
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config_loader import CFG, open_browser

from tools import dev_tools as dt


def _output_root():
    return CFG.get("project_builder", {}).get(
        "output_root", "C:/Users/soura/Documents/Default Project/jarvis/builds"
    )


def _repair_json(s):
    # close unterminated string
    if s.count('"') % 2 == 1:
        s += '"'
    # close unterminated objects/arrays using a stack
    opens = []
    in_str = False
    esc = False
    for ch in s:
        if esc:
            esc = False
            continue
        if ch == '\\':
            esc = True
        elif ch == '"':
            in_str = not in_str
        elif not in_str:
            if ch in "{[":
                opens.append(ch)
            elif ch in "}]":
                if opens:
                    opens.pop()
    close_map = {"{": "}", "[": "]"}
    while opens:
        s += close_map[opens.pop()]
    return s


def _extract_object(s):
    start = s.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if esc:
            esc = False
            continue
        if ch == '\\':
            esc = True
        elif ch == '"':
            in_str = not in_str
        elif not in_str:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return s[start:i + 1]
    return None


def _quote_keys(s):
    # turn JS-object style { key: ... } into strict JSON { "key": ... }
    return re.sub(r'([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*(\s*:)', r'\1"\2"\3', s)


def _llm_json(prompt, system, tier="cloud_heavy"):
    try:
        import llm
        resp, _ = llm.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ], tools=None, tier=tier)
        content = resp.get("content", "")
        obj = _extract_object(content)
        if not obj:
            return None, f"No JSON in LLM response: {content[:200]}"
        for attempt in (obj, _repair_json(obj), _quote_keys(obj), _quote_keys(_repair_json(obj))):
            try:
                return json.loads(attempt), None
            except json.JSONDecodeError:
                continue
        return None, f"JSON parse error: {content[:200]}"
    except Exception as e:
        return None, f"LLM error: {type(e).__name__}: {e}"


def _parse_file_blocks(text):
    files = {}
    cur = None
    buf = []
    for line in text.split("\n"):
        m = re.match(r"^=+\s*(.+?)\s*=+\s*$", line)
        if m:
            if cur is not None:
                files[cur] = "\n".join(buf).rstrip("\n")
            cur = m.group(1).strip()
            buf = []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        files[cur] = "\n".join(buf).rstrip("\n")
    return files


def _llm_files(prompt, system, tier="cloud_heavy"):
    sys_instr = (
        system + "\n\nIMPORTANT FORMAT: Output each file as a block. On its own line write "
        "'=== relative/path.ext ===' then the full file content on the following lines. "
        "Do NOT wrap in JSON and do NOT use markdown ``` fences. Separate multiple files with "
        "their own '=== name ===' lines. No extra commentary outside the file blocks."
    )
    try:
        import llm
        resp, _ = llm.chat([
            {"role": "system", "content": sys_instr},
            {"role": "user", "content": prompt},
        ], tools=None, tier=tier)
        content = resp.get("content", "")
    except Exception as e:
        return None, f"LLM error: {type(e).__name__}: {e}"
    files = _parse_file_blocks(content)
    if not files:
        return None, f"No file blocks found: {content[:200]}"
    return files, None


def _finalize(files, name, preview_file=None, run_cmd=None, summary=None):
    root = os.path.join(_output_root(), name)
    os.makedirs(root, exist_ok=True)
    written = []
    for rel, content in files.items():
        if not isinstance(content, str):
            content = json.dumps(content, indent=2)
        fp = os.path.join(root, rel)
        os.makedirs(os.path.dirname(os.path.abspath(fp)), exist_ok=True)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        written.append(rel)
    notes = []
    if preview_file and preview_file.endswith(".html"):
        url = "file://" + os.path.join(root, preview_file)
        try:
            open_browser(url)
            notes.append(f"Preview opened: {url}")
        except Exception:
            pass
    elif run_cmd:
        try:
            r = subprocess.run(run_cmd, shell=True, capture_output=True, text=True, cwd=root, timeout=30)
            notes.append(f"Run '{run_cmd}': {(r.stdout or r.stderr or '').strip()[:300]}")
        except Exception as e:
            notes.append(f"Run failed: {e}")
    return (
        f"✅ {'Project' if summary is None else 'Done'}: {summary or name}\n"
        f"📁 {root}\n📄 {written}\n"
        + ("\n".join(notes) if notes else "")
    )


def build_project(description, name=None):
    if name is None:
        name = re.sub(r"[^a-zA-Z0-9_]", "_", description.strip().lower())[:40] or "project"
    system = "Tum ek expert full-stack developer ho. User ne ek project banane ko kaha. Multiple files banao, sab complete aur working. Production quality code ho."
    files, err = _llm_files(f"Project banao: {description}", system, tier="cloud_heavy")
    if err:
        return f"Build fail: {err}"
    return _finalize(files, name, summary=f"Project: {description[:60]}")


def build_website(description, name=None, framework="html"):
    if name is None:
        name = re.sub(r"[^a-zA-Z0-9_]", "_", description.strip().lower())[:40] or "website"
    if framework == "html":
        system = "Tum web developer ho. Ek complete, modern, responsive website banao (HTML + CSS + JS). Mobile-responsive, attractive, working ho. Files: index.html, style.css, script.js (aur jo zarurat ho)."
        files, err = _llm_files(f"Website banao: {description} (pure HTML/CSS/JS, no build step)", system, tier="cloud_heavy")
        if err:
            return f"Website build fail: {err}"
        return _finalize(files, name, preview_file="index.html", summary=f"Website: {description[:60]}")
    system = f"Tum web developer ho. {framework} project banao (multiple files)."
    files, err = _llm_files(f"Website banao ({framework}): {description}", system, tier="cloud_heavy")
    if err:
        return f"Website build fail: {err}"
    return _finalize(files, name, run_cmd="npm install && npm run dev", summary=f"{framework} Website: {description[:50]}")


def build_game(description, name=None, kind="pygame"):
    if name is None:
        name = re.sub(r"[^a-zA-Z0-9_]", "_", description.strip().lower())[:40] or "game"
    if kind == "pygame":
        system = "Tum Python pygame game developer ho. Ek complete, playable pygame game banao. Game window, loop, input, exit ho. Files: main.py (aur README.txt agar chahiye)."
        files, err = _llm_files(f"Pygame game banao: {description}", system, tier="cloud_heavy")
        if err:
            return f"Game build fail: {err}"
        root = os.path.join(_output_root(), name)
        res = _finalize(files, name, summary=f"Game: {description[:50]}")
        try:
            subprocess.Popen(
                [sys.executable, os.path.join(root, "main.py")],
                cwd=root, creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            res += "\n🎮 Game launch ho gaya (new window)"
        except Exception as e:
            res += f"\nLaunch failed: {e}"
        return res
    system = "Tum web game developer ho. Ek complete HTML5 canvas game banao (single index.html with embedded CSS/JS)."
    files, err = _llm_files(f"HTML5 canvas game banao: {description}", system, tier="cloud_heavy")
    if err:
        return f"Game build fail: {err}"
    return _finalize(files, name, preview_file="index.html", summary=f"HTML5 Game: {description[:50]}")


def _android_toolchain_ready():
    has_buildozer = shutil.which("buildozer") is not None
    java = shutil.which("java") is not None or bool(os.environ.get("JAVA_HOME"))
    android = bool(os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT"))
    return has_buildozer and java and android


def build_android_native(description, name=None):
    if name is None:
        name = re.sub(r"[^a-zA-Z0-9_]", "_", description.strip().lower())[:40] or "android_app"
    system = ("Tum expert Python/Kivy mobile developer ho. Ek NATIVE Android app banao jo Buildozer se "
              "asli .apk banayega. Sirf Kivy use karo (koi extra pip dependency nahi). "
              "Files: main.py (full Kivy code, self-contained, runnable), buildozer.spec (build config). "
              "UI mobile-friendly ho.")
    files, err = _llm_files(f"Native Android (Kivy) app banao: {description}", system, tier="cloud_heavy")
    if err:
        return f"Native Android build fail: {err}"
    root = os.path.join(_output_root(), name + "_native")
    os.makedirs(root, exist_ok=True)
    if "main.py" not in files:
        files["main.py"] = "from kivy.app import App\nfrom kivy.uix.label import Label\nclass M(App):\n    def build(self):\n        return Label(text='Hello')\nM().run()\n"
    if "buildozer.spec" not in files:
        files["buildozer.spec"] = (
            f"[app]\ntitle = {name}\npackage.name = {name[:20] or 'app'}\n"
            f"package.domain = org.jarvis\nsource.dir = .\nsource.include_exts = py,png,jpg,kv,json\n"
            "version = 0.1\nrequirements = python3,kivy\norientation = portrait\n"
            "android.permissions = INTERNET\nandroid.api = 34\nandroid.minapi = 24\n"
            "android.accept_sdk_license = True\nlog_level = 1\n"
        )
    written = []
    for rel, content in files.items():
        fp = os.path.join(root, rel)
        os.makedirs(os.path.dirname(os.path.abspath(fp)), exist_ok=True)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content if isinstance(content, str) else json.dumps(content, indent=2))
        written.append(rel)
    notes = [f"📁 Native project: {root}", f"📄 {written}"]
    if _android_toolchain_ready():
        try:
            r = subprocess.run("buildozer android debug", shell=True, capture_output=True,
                               text=True, cwd=root, timeout=1800)
            out = (r.stdout or r.stderr or "")[:400]
            apk = None
            for f in os.listdir(os.path.join(root, "bin")) if os.path.isdir(os.path.join(root, "bin")) else []:
                if f.endswith(".apk"):
                    apk = os.path.join(root, "bin", f)
            if apk:
                notes.append(f"✅ APK ban gaya: {apk}")
            else:
                notes.append(f"Build try hua par APK nahi mila:\n{out}")
        except Exception as e:
            notes.append(f"APK build fail: {e}")
    else:
        notes.append("⚠️ Native APK compile ke liye toolchain chahiye (Java + Android SDK + Buildozer).")
        notes.append("Setup: pip install buildozer, Java + Android SDK install karo, fir is folder mein: buildozer android debug")
    return (
        f"✅ Native Android project ready: {description[:50]}\n"
        + "\n".join(notes)
    )


def build_android_app(description, name=None):
    if name is None:
        name = re.sub(r"[^a-zA-Z0-9_]", "_", description.strip().lower())[:40] or "android_app"
    system = ("Tum mobile web developer ho. Ek PWA (Progressive Web App) banao jo Android phone par "
              "install ho sakta hai ('Add to Home Screen'). Mobile-first, responsive, offline-capable ho. "
              "Files: index.html, style.css, app.js, manifest.json, sw.js (aur jo zarurat ho).")
    files, err = _llm_files(f"Android PWA app banao: {description}", system, tier="cloud_heavy")
    if err:
        return f"Android app build fail: {err}"
    root = os.path.join(_output_root(), name)
    res = _finalize(files, name, preview_file="index.html", summary=f"Android app: {description[:50]}")
    res += "\n📱 Android par: Chrome se open karo → Menu → 'Add to Home Screen' se install karo"
    native = build_android_native(description, name)
    return res + "\n\n" + native


if __name__ == "__main__":
    print(build_project("ek calculator web app"))
