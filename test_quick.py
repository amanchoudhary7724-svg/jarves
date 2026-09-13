"""Quick agent test."""
import asyncio, sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(errors="replace")
from agent import JarvisAgent

async def t():
    a = JarvisAgent()
    for text, lang in [("notepad band karo", "hi"), ("what can you do", "en"), ("tell me a joke", "en")]:
        r, e = await a.handle(text, lang=lang)
        print(f"[{text}] => {r[:120]}")

asyncio.run(t())
