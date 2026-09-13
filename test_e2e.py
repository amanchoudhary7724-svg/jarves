"""Full end-to-end test of all rules + LLM."""
import asyncio
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(errors="replace")

from agent import JarvisAgent

async def test():
    agent = JarvisAgent()
    print(f"Tools: {len(agent._schemas)}")
    
    tests = [
        ("namaste", "hi", "Greeting"),
        ("time kya hai", "hi", "Time"),
        ("aaj ki date kya hai", "hi", "Date"),
        ("calculator kholo", "hi", "Open app"),
        ("notepad band karo", "hi", "Close app"),
        ("volume 50", "hi", "Volume"),
        ("screenshot le lo", "hi", "Screenshot"),
        ("copy karo", "hi", "Copy"),
        ("paste karo", "hi", "Paste"),
        ("click karo", "hi", "Click"),
        ("system info", "en", "System info"),
        ("weather kaisa hai", "hi", "Weather"),
        ("kya haal hai", "hi", "Greeting 2"),
        ("youtube par romantic song play karo", "hi", "YouTube play"),
        ("search for python tutorial on youtube", "en", "YouTube search"),
        ("google search python", "en", "Web search"),
        ("mera battery kitna hai", "hi", "Battery"),
        ("brightness 70", "hi", "Brightness"),
        ("what can you do", "en", "LLM conversational"),
        ("tell me a joke", "en", "LLM joke"),
    ]
    
    for text, lang, desc in tests:
        print(f"\n--- {desc} ---")
        print(f"Input: {text!r}")
        resp, emotion = await agent.handle(text, lang=lang)
        print(f"Response: {resp[:120]}")
        print(f"Emotion: {emotion}")

if __name__ == "__main__":
    asyncio.run(test())
