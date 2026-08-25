import sys, os, types

# Stub pygame (audio playback only; not needed for a text preview).
# Your real jarvis_env (Python 3.11) has the real pygame installed.
class _Dummy:
    def __getattr__(self, name):
        return _Dummy()
    def __call__(self, *a, **k):
        return _Dummy()
pyg = types.ModuleType("pygame")
pyg.mixer = _Dummy()
pyg.init = lambda *a, **k: None
pyg.quit = lambda *a, **k: None
sys.modules["pygame"] = pyg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent import JarvisAgent

a = JarvisAgent()
samples = [
    "namaste jarvis",
    "time kya hai",
    "website banao ek portfolio",
    "jarvis ek calculator project banao",
]
for cmd in samples:
    try:
        resp, emotion = a.handle(cmd)
    except Exception as e:
        resp, emotion = f"[ERROR {type(e).__name__}: {e}]", "neutral"
    print(f"\nAap    : {cmd}")
    print(f"Jarvis : {resp}   [{emotion}]")
print("\n" + "=" * 50)
print("  JARVIS PREVIEW COMPLETE")
print("=" * 50)
