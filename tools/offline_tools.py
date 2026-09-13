import ctypes
import datetime
import os
import subprocess
import logging

import psutil
import pyautogui

from config_loader import CFG, open_browser

pyautogui.FAILSAFE = True

log = logging.getLogger(__name__)

# Critical processes that must not be force-killed
_CRITICAL_PROCESSES = frozenset([
    "explorer", "svchost", "csrss", "lsass", "winlogon",
    "services", "dwm", "system", "smss", "wininit",
])


def _resolve_app(name):
    name = name.lower().strip()
    paths = CFG.get("app_paths", {})
    if name in paths:
        return paths[name]
    for key, val in paths.items():
        if key in name or name in key:
            return val
    return name


def open_app(name):
    target = _resolve_app(name)
    if str(target).startswith("http"):
        open_browser(target)
        return f"{name} khol diya."
    try:
        os.startfile(str(target))
        return f"{name} khol diya."
    except Exception:
        try:
            subprocess.Popen(["cmd", "/c", "start", "", str(target)], shell=False)
            return f"{name} khol diya."
        except Exception as e:
            return f"{name} nahi khul paya: {e}"


def close_app(name):
    name_clean = name.lower().strip().removesuffix(".exe")
    if name_clean in _CRITICAL_PROCESSES:
        return f"BLOCKED: '{name}' ek critical system process hai. Isko band karna system crash kar sakta hai."
    names = CFG.get("executable_names", {})
    exe = names.get(name.lower().strip(), f"{name}.exe")
    exe_clean = exe.lower().removesuffix(".exe")
    if exe_clean in _CRITICAL_PROCESSES:
        return f"BLOCKED: '{name}' maps to critical system process '{exe}'. Band nahi karunga."
    result = subprocess.run(["taskkill", "/IM", exe, "/F"], capture_output=True, text=True)
    if result.returncode == 0:
        return f"{name} band kar diya."
    return f"{name} band nahi hua, shayad chal hi nahi raha."


def _get_volume_obj():
    import pyautogui

    try:
        from ctypes import POINTER, cast
        import comtypes
        from comtypes import CLSCTX_ALL, CoInitialize
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        CoInitialize()
        devices = AudioUtilities.GetSpeakers()
        if hasattr(devices, "Activate"):
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            return cast(interface, POINTER(IAudioEndpointVolume))
    except Exception:
        pass
    return None


def set_volume(percent):
    percent = max(0, min(100, int(percent)))
    vol = _get_volume_obj()
    if vol is not None:
        vol.SetMasterVolumeLevelScalar(percent / 100.0, None)
        vol.SetMute(0, None)
        return f"Volume {percent} percent kar diya."
    import subprocess

    subprocess.run(
        ["powershell", "-Command",
         f"$wsh = New-Object -ComObject WScript.Shell; 1..{percent} | ForEach-Object {{$wsh.SendKeys([char]175)}}"],
        capture_output=True,
    )
    return f"Volume {percent} percent kar diya."


def change_volume(delta):
    vol = _get_volume_obj()
    if vol is not None:
        current = int(vol.GetMasterVolumeLevelScalar() * 100)
        return set_volume(current + delta)
    import pyautogui

    if delta > 0:
        for _ in range(abs(delta) // 2):
            pyautogui.press("volumeup")
    else:
        for _ in range(abs(delta) // 2):
            pyautogui.press("volumedown")
    return "Volume adjust kar diya."


def toggle_mute(mute):
    vol = _get_volume_obj()
    if vol is not None:
        vol.SetMute(1 if mute else 0, None)
        return "Mute kar diya." if mute else "Unmute kar diya."
    import pyautogui

    pyautogui.press("volumemute")
    return "Mute toggle kar diya."


def media_control(action):
    keys = {
        "play": "playpause",
        "pause": "playpause",
        "next": "nexttrack",
        "previous": "prevtrack",
        "stop": "stopmedia",
    }
    action = action.lower().strip()
    if action not in keys:
        return f"Media action '{action}' samajh nahi aaya."
    pyautogui.press(keys[action])
    return f"Music {action} kar diya."


def take_screenshot():
    path = os.path.join(os.path.expanduser("~"), "Pictures", "jarvis_screenshot.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pyautogui.screenshot(path)
    return "Screenshot le liya, Pictures folder mein save kar diya."


def lock_pc():
    ctypes.windll.user32.LockWorkStation()
    return "PC lock kar raha hoon."


def battery_status():
    battery = psutil.sensors_battery()
    if battery is None:
        return "Battery ki jaankari nahi mil rahi."
    percent = int(battery.percent)
    charging = "charging chal rahi hai" if battery.power_plugged else "battery par chal raha hai"
    mins = int(battery.secsleft / 60) if battery.secsleft > 0 else 0
    extra = f", lagbhag {mins} minute bache hain" if mins else ""
    return f"Battery {percent} percent hai, {charging}{extra}."


def get_time(kind="time"):
    now = datetime.datetime.now()
    if kind in ("date", "din", "tareekh"):
        days = ["Somvaar", "Mangalvaar", "Budhvaar", "Guruvaar", "Shukravaar", "Shanivaar", "Ravivaar"]
        months = ["January", "February", "March", "April", "May", "June", "July",
                  "August", "September", "October", "November", "December"]
        return f"Aaj {days[now.weekday()]} hai, {now.day} {months[now.month - 1]} {now.year}."
    h, m = now.hour, now.minute
    ampm = "baje subah" if h < 12 else ("baje dopahar" if h < 17 else ("baje shaam" if h < 21 else "baje raat"))
    h12 = h % 12 or 12
    return f"Abhi {h12}:{m:02d} {ampm} ho rahe hain."


def type_text(text):
    try:
        pyautogui.typewrite(text, interval=0.02)
        return "Type kar diya."
    except Exception:
        return "Typing fail hui, sirf English text support hai is mode mein."


def shutdown_pc(mode="shutdown"):
    if not CFG.get("developer", {}).get("confirm_destructive", True):
        return f"BLOCKED: {mode} blocked. confirm_destructive config mein 'false' karo (yeh destructive operation hai)."
    flag = {"shutdown": "/s", "restart": "/r", "sleep": "/h"}.get(mode, "/s")
    if flag == "/h":
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        log.warning("PC put to sleep")
        return "Sleep mode mein ja raha hoon."
    subprocess.run(["shutdown", flag, "/t", "60"])
    log.warning("PC shutdown/restart scheduled: mode=%s", mode)
    return f"60 second mein PC {mode} hoga. Rokna ho toh boliye 'cancel'."


def abort_shutdown():
    subprocess.run(["shutdown", "/a"])
    return "Shutdown cancel kar diya."

