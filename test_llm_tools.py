"""Test: force LLM path for tool-calling verification."""
import asyncio
import sys
sys.path.insert(0, ".")
# Fix Windows console encoding for emoji/unicode output
sys.stdout.reconfigure(errors="replace")

from agent import JarvisAgent
from llm import has_internet, nvidia_ready

async def test():
    agent = JarvisAgent()
    print(f"Schemas loaded: {len(agent._schemas)} tools")
    print(f"Internet: {has_internet()}, NVIDIA: {nvidia_ready()}")
    
    # Test 1: command that has NO rule match -> must go through LLM
    print("\n--- Test 1: LLM path (brightness) ---")
    resp, emotion = await agent.handle("dim the screen brightness to 30 percent", lang="en")
    print(f"Response: {resp}")
    print(f"Emotion: {emotion}")
    
    # Test 2: Another non-rule command
    print("\n--- Test 2: LLM path (YouTube search) ---")
    resp, emotion = await agent.handle("search for lofi beats on youtube", lang="en")
    print(f"Response: {resp}")
    print(f"Emotion: {emotion}")
    
    # Test 3: Hindi non-rule command
    print("\n--- Test 3: LLM path (Hindi battery) ---")
    resp, emotion = await agent.handle("mera battery kitna hai", lang="hi")
    print(f"Response: {resp}")
    print(f"Emotion: {emotion}")

if __name__ == "__main__":
    asyncio.run(test())
