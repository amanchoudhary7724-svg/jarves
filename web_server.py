import asyncio
import os
import sys
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import JarvisAgent, _detect_lang

app = FastAPI(title="JARVIS Avatar Server")

allowed_origins = [
    origin.strip()
    for origin in os.getenv("JARVIS_ALLOWED_ORIGINS", "http://127.0.0.1:8765,http://localhost:8765").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

UI_DIR = Path(__file__).parent

agent = JarvisAgent()

class ChatRequest(BaseModel):
    text: str
    lang: str = "hi"

class ChatResponse(BaseModel):
    reply: str
    emotion: str = "neutral"

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    resp, emotion = await agent.handle(req.text, lang=req.lang)
    return ChatResponse(reply=resp, emotion=emotion)

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    origin = ws.headers.get("origin")
    if origin not in allowed_origins:
        await ws.close(code=1008)
        return
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            text = data.get("text", "")
            lang = data.get("lang", "hi")
            resp, emotion = await agent.handle(text, lang=lang)
            await ws.send_json({"reply": resp, "emotion": emotion})
    except WebSocketDisconnect:
        pass

app.mount("/static", StaticFiles(directory=UI_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    index_file = UI_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>JARVIS UI not found</h1>", status_code=404)

@app.get("/health")
async def health():
    return {"status": "ok", "agent": "JARVIS"}

def run_server(host: str = "127.0.0.1", port: int = 8765):
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")

if __name__ == "__main__":
    run_server()
