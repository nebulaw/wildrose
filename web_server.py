import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
from ai import LLMBrain
from characters.character import ST_IDLE, ST_RUN, ST_RUSH, ST_DAMAGE, ST_DIE

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/web", StaticFiles(directory="web"), name="web")


@app.get("/")
async def get_index():
    return FileResponse("web/index.html")


# Define Bridge classes so AI logic can push to WebSocket
class WebChatBridge:
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.loop = asyncio.get_running_loop()

    def add_message(self, text: str, sender: str = "system"):
        try:
            asyncio.run_coroutine_threadsafe(
                self.ws.send_json({"type": "chat", "text": text, "sender": sender}),
                self.loop,
            )
        except Exception:
            pass

    def set_typing(self, is_typing: bool):
        try:
            asyncio.run_coroutine_threadsafe(
                self.ws.send_json({"type": "typing", "state": is_typing}), self.loop
            )
        except Exception:
            pass

    def remove_last_message(self):
        pass


class WebCharBridge:
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.loop = asyncio.get_running_loop()
        self.action = ST_IDLE
        self.alive = True

    def set_action(self, action=ST_IDLE):
        self.action = action
        try:
            asyncio.run_coroutine_threadsafe(
                self.ws.send_json({"type": "action", "action": action}), self.loop
            )
        except Exception:
            pass

    def purr(self):
        try:
            asyncio.run_coroutine_threadsafe(
                self.ws.send_json({"type": "sound", "sound": "purr"}), self.loop
            )
        except Exception:
            pass

    def meow(self):
        try:
            asyncio.run_coroutine_threadsafe(
                self.ws.send_json({"type": "sound", "sound": "meow"}), self.loop
            )
        except Exception:
            pass

    def purr(self):
        asyncio.run_coroutine_threadsafe(
            self.ws.send_json({"type": "sound", "sound": "purr"}), self.loop
        )

    def meow(self):
        asyncio.run_coroutine_threadsafe(
            self.ws.send_json({"type": "sound", "sound": "meow"}), self.loop
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    chat_bridge = WebChatBridge(websocket)
    char_bridge = WebCharBridge(websocket)

    # Initialize the LLMBrain with the bridge instead of Pygame UI
    brain = LLMBrain(character=char_bridge, chat_handler=chat_bridge)

    # Background task for autonomous brain loop
    async def brain_loop():
        while True:
            brain.update()
            await asyncio.sleep(1)

    loop_task = asyncio.create_task(brain_loop())

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)

            if payload.get("type") == "chat":
                msg = payload.get("text")
                brain.process_user_message(msg)
            elif payload.get("type") == "pet":
                # Handle petting interaction
                char_bridge.set_action(ST_DAMAGE)
                # optionally process a silent user message to trigger proactivity
                # brain.process_user_message("*pets you*")
    except WebSocketDisconnect:
        loop_task.cancel()


if __name__ == "__main__":
    print("Starting Web Server for Wildrose on http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
