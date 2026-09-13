"""Network diagnostics - ONLY for your own PC/network. No external scanning."""
import subprocess
import socket
import psutil
import time

def _safe_run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=False)
        return r.stdout.strip() or r.stderr.strip()
    except Exception as e:
        return f"Error: {e}"

def diagnose_network():
    """Full network diagnosis for YOUR PC only."""
    lines = ["=== NETWORK DIAGNOSIS (apna system) ==="]
    
    # IP & gateway
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        lines.append(f"Local IP: {local_ip}")
    except: lines.append("Local IP: nahi mila")
    
    # Gateway
    try:
        out = _safe_run(["ipconfig"], timeout=8)
        for l in out.splitlines():
            if "Default Gateway" in l and ":" in l:
                gw = l.split(":")[-1].strip()
                if gw and gw != "0.0.0.0":
                    lines.append(f"Gateway: {gw}")
                    break
    except: pass
    
    # WiFi info
    try:
        out = _safe_run(["netsh", "wlan", "show", "interfaces"])
        for l in out.splitlines():
            if "SSID" in l and "BSSID" not in l:
                lines.append(l.strip())
            if "Signal" in l or "State" in l or "Channel" in l:
                lines.append(l.strip())
    except: pass
    
    # Internet check
    try:
        s = socket.create_connection(("8.8.8.8", 53), timeout=3)
        s.close()
        lines.append("Internet: CONNECTED")
    except: lines.append("Internet: DISCONNECTED")
    
    # Interfaces
    try:
        addrs = psutil.net_if_addrs()
        for iface, snics in addrs.items():
            if "Loopback" in iface: continue
            for snic in snics:
                if snic.family == socket.AF_INET:
                    lines.append(f"{iface}: {snic.address}")
    except: pass
    
    return "\n".join(lines)

def wifi_diagnostics():
    """Apna WiFi ka full status - signal, channel, security."""
    out = _safe_run(["netsh", "wlan", "show", "interfaces"])
    if not out or "Error" in out: return "WiFi info nahi mila. WiFi on hai?"
    # Also show saved profiles
    profiles = _safe_run(["netsh", "wlan", "show", "profiles"])
    return out + "\n\n--- Saved Profiles ---\n" + profiles

def wifi_password(profile=None):
    """Apna hi saved WiFi password dekho - dusre ka nahi."""
    if not profile:
        return "Profile naam do. Jaise: wifi_password MyWiFi"
    # Only allow viewing OWN saved profiles, not hacking
    result = _safe_run(["netsh", "wlan", "show", "profile", f"name={profile}", "key=clear"])
    for l in result.splitlines():
        if "Key Content" in l or "KeyContent" in l:
            return l.strip()
    return f"'{profile}' ka password nahi mila ya profile nahi hai. wifi_diagnostics se naam check karo."

def check_local_ports():
    """Sirf localhost (127.0.0.1) pe kaunse ports khule hain - apna PC only."""
    common = [135, 445, 3306, 5432, 8000, 8080, 3000, 5000, 7860, 11434]
    lines = ["Localhost ports (127.0.0.1):"]
    for port in common:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        try:
            result = s.connect_ex(("127.0.0.1", port))
            status = "OPEN" if result == 0 else "closed"
            if result == 0:
                try: svc = socket.getservbyport(port)
                except: svc = "unknown"
                lines.append(f"  {port:5d} {status} ({svc})")
        finally: s.close()
    # Also show listening connections
    try:
        conns = psutil.net_connections(kind='inet')
        listening = [c for c in conns if c.status == 'LISTEN' and c.laddr.ip == '127.0.0.1']
        if listening:
            lines.append("\nListening on localhost:")
            for c in listening[:10]:
                lines.append(f"  {c.laddr.ip}:{c.laddr.port} pid={c.pid}")
    except: pass
    return "\n".join(lines)

def ping_test(target="127.0.0.1"):
    """Ping test - only localhost aur gateway allowed. External ping block hai."""
    allowed = ["127.0.0.1", "localhost"]
    # Add gateway dynamically
    try:
        out = _safe_run(["ipconfig"], timeout=5)
        for l in out.splitlines():
            if "Default Gateway" in l and ":" in l:
                gw = l.split(":")[-1].strip()
                if gw: allowed.append(gw)
    except: pass
    # Also allow 8.8.8.8 for internet check
    allowed.append("8.8.8.8")
    
    target = target.strip()
    if target not in allowed:
        return f"BLOCKED: Sirf ye allowed hain: {', '.join(allowed)}. External host ping nahi kar sakte (safety)."
    result = _safe_run(["ping", "-n", "2", target], timeout=8)
    return result[:1500]

def ip_config():
    """ipconfig jaisa full network config."""
    return _safe_run(["ipconfig", "/all"], timeout=10)[:4000]
