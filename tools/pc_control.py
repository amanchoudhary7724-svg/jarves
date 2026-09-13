import os
import subprocess
import time
import logging

import pyautogui
import psutil

from config_loader import CFG, open_browser

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

log = logging.getLogger(__name__)

# Critical Windows processes that must never be killed
_CRITICAL_PROCESSES = frozenset([
    "system", "system idle process", "smss", "csrss",
    "wininit", "services", "lsass", "svchost",
    "winlogon", "dwm", "explorer", "taskhostw",
    "sihost", "taskhost", "fontdrvhost",
])


def _combo(keys):
    parts = [k.strip().lower() for k in keys.replace("+", " ").split() if k.strip()]
    aliases = {
        "win": "win", "windows": "win", "ctrl": "ctrl", "control": "ctrl",
        "alt": "alt", "shift": "shift", "enter": "enter", "return": "enter",
        "esc": "esc", "escape": "esc", "tab": "tab", "space": "space",
        "up": "up", "down": "down", "left": "left", "right": "right",
    }
    mapped = [aliases.get(p, p) for p in parts]
    pyautogui.hotkey(*mapped)
    return "+".join(mapped)


def minimize_window():
    _combo("win down")
    return "Window minimize kar diya."


def maximize_window():
    _combo("win up")
    return "Window maximize kar diya."


def close_window():
    _combo("alt f4")
    return "Window band kar diya."


def switch_window(n=1):
    n = max(1, min(int(n or 1), 10))
    pyautogui.keyDown("alt")
    for _ in range(n):
        pyautogui.press("tab")
        time.sleep(0.15)
    pyautogui.keyUp("alt")
    return f"{n} window aage badha diya."


def show_desktop():
    _combo("win d")
    return "Desktop dikha diya."


def focus_app(name):
    import pygetwindow as gw
    target = (name or "").lower().strip()
    for w in gw.getAllWindows():
        title = (w.title or "").lower()
        if target and target in title:
            try:
                if w.isMinimized:
                    w.restore()
                w.activate()
                return f"'{w.title}' window pe focus kar diya."
            except Exception:
                continue
    return f"'{name}' koi visible window nahi mili."


def press_key(combo):
    if not combo:
        return "Key combo khali hai."
    _combo(combo)
    return f"'{combo}' press kar diya."


def type_text(text):
    try:
        pyautogui.write(text, interval=0.02)
        return "Type kar diya."
    except Exception:
        return "Typing fail hui, sirf English text support hai."


def mouse_click(button="left"):
    btn = "right" if str(button).lower() in ("right", "dain", "rightclick") else "left"
    pyautogui.click(button=btn)
    return f"{btn} click kar diya."


def double_click():
    pyautogui.doubleClick()
    return "Double click kar diya."


def mouse_move(x, y):
    x = int(x)
    y = int(y)
    sw, sh = pyautogui.size()
    x = max(0, min(x, sw - 1))
    y = max(0, min(y, sh - 1))
    pyautogui.moveTo(x, y, duration=0.2)
    return f"Mouse ({x},{y}) pe le gaya."


def scroll(amount):
    amt = int(amount)
    amt = max(-20, min(amt, 20))
    pyautogui.scroll(amt * 60)
    return f"Scroll {'up' if amt > 0 else 'down'} kar diya."


def set_brightness(percent):
    percent = max(0, min(100, int(percent)))
    ps = (
        "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
        f".WmiSetBrightness(1,{percent})"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode == 0:
        return f"Brightness {percent} percent kar diya."
    return "Brightness control is PC par available nahi hai (external monitor ya desktop)."


def get_brightness():
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"],
        capture_output=True, text=True, timeout=15,
    )
    try:
        return int(result.stdout.strip())
    except Exception:
        return None


def brightness_change(delta):
    current = get_brightness()
    if current is None:
        return "Brightness control is PC par available nahi hai."
    return set_brightness(current + int(delta))


def clipboard_write(text):
    import pyperclip
    pyperclip.copy(str(text))
    return "Clipboard pe copy kar diya."


def clipboard_read():
    import pyperclip
    data = pyperclip.paste() or ""
    if not data.strip():
        return "Clipboard khali hai."
    snippet = data[:400] + ("..." if len(data) > 400 else "")
    return f"Clipboard mein hai:\n{snippet}"


def system_info():
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")
    lines = [
        f"CPU: {cpu:.0f}% used",
        f"RAM: {ram.percent:.0f}% used ({ram.used // (1024**3)}GB / {ram.total // (1024**3)}GB)",
        f"Disk C: {disk.percent:.0f}% full ({disk.free // (1024**3)}GB free)",
    ]
    battery = psutil.sensors_battery()
    if battery:
        plug = ", charging" if battery.power_plugged else ""
        lines.append(f"Battery: {int(battery.percent)}%{plug}")
    return "\n".join(lines)


def list_processes(sort_by="cpu"):
    procs = []
    for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
        try:
            info = p.info
            procs.append(info)
        except Exception:
            continue
    key = "memory_percent" if str(sort_by).lower() in ("ram", "memory", "mem") else "cpu_percent"
    top = sorted(procs, key=lambda x: x.get(key) or 0, reverse=True)[:12]
    lines = [f"{'PID':>7}  {'CPU%':>5}  {'MEM%':>5}  Name"]
    for p in top:
        lines.append(
            f"{p.get('pid', 0):>7}  {p.get('cpu_percent') or 0:>5.1f}  "
            f"{p.get('memory_percent') or 0:>5.1f}  {p.get('name', '?')}"
        )
    return "\n".join(lines)


def kill_process(target):
    target = str(target).strip().lower()
    # Block killing critical system processes
    clean = target.removesuffix(".exe").lower()
    if clean in _CRITICAL_PROCESSES:
        log.warning("Blocked kill of critical process: %s", target)
        return f"BLOCKED: '{target}' ek critical system process hai. Isko kill karna system crash kar sakta hai."
    killed = 0
    for p in psutil.process_iter(["pid", "name"]):
        try:
            name = (p.info.get("name") or "").lower()
            name_clean = name.removesuffix(".exe")
            # Skip critical processes even if matched by substring
            if name_clean in _CRITICAL_PROCESSES:
                continue
            if target.isdigit():
                if p.info.get("pid") == int(target):
                    p.kill()
                    killed += 1
            elif target in name or target.removesuffix(".exe") in name:
                p.kill()
                killed += 1
        except Exception:
            continue
    if killed:
        log.info("Killed %d processes matching '%s'", killed, target)
        return f"{killed} process ('{target}') band kar diye."
    return f"'{target}' naam ka koi process nahi mila."


def network_info():
    ssid = ""
    try:
        out = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=10,
        ).stdout
        for line in out.splitlines():
            if "SSID" in line and "BSSID" not in line:
                ssid = line.split(":", 1)[1].strip()
                break
    except Exception:
        pass
    ip = ""
    try:
        import socket as _socket
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    parts = []
    if ssid:
        parts.append(f"WiFi: {ssid}")
    if ip:
        parts.append(f"IP: {ip}")
    return "\n".join(parts) if parts else "Network info nahi mil paya."


def search_files(name, location=None):
    name = (name or "").lower().strip()
    if not name:
        return "File ka naam do."
    roots = [location] if location else [
        os.path.expanduser("~\\Documents"),
        os.path.expanduser("~\\Downloads"),
        os.path.expanduser("~\\Pictures"),
        os.path.expanduser("~\\Desktop"),
        os.path.expanduser("~\\Videos"),
    ]
    results = []
    for root in roots:
        root = os.path.expandvars(os.path.expanduser(root))
        if not os.path.isdir(root):
            continue
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                       ("node_modules", "__pycache__", "venv", ".git")]
            for f in files + dirs:
                if name in f.lower():
                    results.append(os.path.join(dirpath, f))
                    if len(results) >= 20:
                        break
            if len(results) >= 20:
                break
        if len(results) >= 20:
            break
    if not results:
        return f"'{name}' kuch nahi mila."
    lines = [f"'{name}' ke {len(results)} matches:"]
    lines.extend(f"- {r}" for r in results)
    return "\n".join(lines)


def create_folder(path):
    path = os.path.expandvars(os.path.expanduser(str(path).strip("\"'")))
    try:
        os.makedirs(path, exist_ok=True)
        return f"Folder ready: {path}"
    except Exception as e:
        return f"Folder nahi ban paya: {e}"


def open_folder(path):
    path = os.path.expandvars(os.path.expanduser(str(path).strip("\"'")))
    if not os.path.isdir(path):
        return f"Folder exist nahi karta: {path}"
    os.startfile(path)
    return f"Folder khol diya: {path}"


def empty_recycle_bin():
    if not CFG.get("developer", {}).get("confirm_destructive", True):
        return "Recycle bin clear blocked. confirm_destructive config mein enable karo (yeh risky operation hai)."
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
        capture_output=True, timeout=30,
    )
    log.warning("Recycle bin emptied")
    return "Recycle bin khali kar diya." if result.returncode == 0 else "Recycle bin clear nahi hua."


def shutdown_pc(mode="shutdown"):
    if not CFG.get("developer", {}).get("confirm_destructive", True):
        return f"BLOCKED: {mode} blocked. confirm_destructive config mein enable karo (yeh destructive operation hai)."
    flag = {"shutdown": "/s", "restart": "/r", "sleep": "/h"}.get(mode, "/s")
    if flag == "/h":
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        log.warning("PC put to sleep")
        return "Sleep mode mein ja raha hoon."
    subprocess.run(["shutdown", flag, "/t", "60"])
    log.warning("PC shutdown/restart scheduled: mode=%s", mode)
    return f"60 second mein PC {mode} hoga. Rokna ho toh boliye 'cancel'."

