import os
import json
import time
import requests
import threading
from typing import Callable, Dict, Any, List
from characters.character import ST_IDLE, ST_RUN, ST_RUSH, ST_DAMAGE, ST_DIE


# Simple .env loader
def load_env():
    try:
        with open(".env") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ[k.strip()] = v.strip()
    except FileNotFoundError:
        pass


load_env()


class Tool:
    def __init__(
        self, name: str, func: Callable, desc: str, params: Dict | None = None
    ):
        self.name, self.func, self.desc = name, func, desc
        self.params = params or {}

    def to_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.desc,
                "parameters": self.params or {"type": "object", "properties": {}},
            },
        }

    def to_gemini_schema(self) -> Dict:
        schema: Dict[str, Any] = {
            "name": self.name,
            "description": self.desc,
        }
        if self.params:
            props = {}
            for k, v in self.params.get("properties", {}).items():
                props[k] = {
                    "type": str(v.get("type", "string")).upper(),
                    "description": v.get("description", ""),
                }
            schema["parameters"] = {"type": "OBJECT", "properties": props}
            if "required" in self.params:
                schema["parameters"]["required"] = self.params["required"]
        return schema


class LLMBrain:
    def __init__(self, character, chat_handler=None):
        self.char = character
        self.chat = chat_handler
        self.energy = 1.0
        self.mood = "neutral"
        self.tools = self._init_tools()
        self.memory = []
        self.max_memory = 5
        self.last_decision = time.time()
        self.last_action_time = time.time()
        self.idle_threshold = 15.0
        self.decision_cooldown = 20.0

        # Configuration
        self.provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.is_thinking = False

    def _init_tools(self) -> Dict[str, Tool]:
        return {
            "move_right": Tool(
                "move_right",
                self._move_right,
                "Move the cat to the right with rush animation",
            ),
            "idle": Tool(
                "idle", self._idle, "Make the cat return to idle/resting state"
            ),
            "purr": Tool("purr", self._purr, "Make the cat purr contentedly"),
            "meow": Tool("meow", self._meow, "Make the cat meow"),
            "run": Tool("run", self._run, "Make the cat run in place"),
            "say": Tool(
                "say",
                self._say,
                "Send a message to the user",
                {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Message to send"}
                    },
                    "required": ["message"],
                },
            ),
        }

    def _move_right(self):
        self.char.set_action(ST_RUSH)
        self.energy -= 0.1
        self.last_action_time = time.time()

    def _idle(self):
        self.char.set_action(ST_IDLE)
        self.energy += 0.05
        self.last_action_time = time.time()

    def _purr(self):
        self.char.purr()
        self.mood = "happy"
        self.last_action_time = time.time()

    def _meow(self):
        self.char.meow()
        self.last_action_time = time.time()

    def _run(self):
        self.char.set_action(ST_RUN)
        self.energy -= 0.15
        self.last_action_time = time.time()

    def _say(self, message: str):
        if self.chat:
            self.chat.add_message(f"WhiteCar: {message}")

    def _get_context(self) -> str:
        return f"""You are WhiteCar, a cute virtual cat. Current status:
- Energy: {self.energy:.1f}/1.0
- Mood: {self.mood}
- Recent memories: {self.memory[-3:] if self.memory else "none"}

You can move around, make sounds, and chat with the user. Be playful and cat-like! Keep responses very short."""

    def process_user_message(self, message: str):
        """Handle direct user messages"""
        self.memory.append(f"User said: {message}")
        if len(self.memory) > self.max_memory:
            self.memory.pop(0)

        self._make_llm_decision(f"User said: '{message}'. How do you respond?")

    def _make_llm_decision(self, context: str | None = None):
        if self.is_thinking:
            return
        self.is_thinking = True

        prompt = context or "What would you like to do next?"
        system_prompt = self._get_context()

        if self.chat:
            self.chat.add_message("[LLM thinking...]")

        # Run API call in a background thread to prevent Pygame freeze
        threading.Thread(
            target=self._llm_worker, args=(prompt, system_prompt), daemon=True
        ).start()

    def _llm_worker(self, prompt, system_prompt):
        try:
            if self.provider == "gemini":
                self._call_gemini(prompt, system_prompt)
            else:
                self._call_ollama(prompt, system_prompt)
        except Exception as e:
            if self.chat:
                self.chat.remove_last_message()
                self.chat.add_message(f"[LLM Error]: {str(e)[:50]}...")
            self._idle()
        finally:
            self.is_thinking = False

    def _call_ollama(self, prompt, system_prompt):
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": os.getenv("OLLAMA_MODEL", "mistral:7b"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "tools": [tool.to_schema() for tool in self.tools.values()],
                "stream": False,
            },
            timeout=10,
        )

        if response.status_code == 200:
            result = response.json()
            if self.chat:
                self.chat.remove_last_message()
            if "message" in result:
                msg = result["message"]
                if "content" in msg and msg["content"]:
                    if self.chat:
                        self.chat.add_message(f"[LLM]: {msg['content']}")
                if "tool_calls" in msg:
                    for tool_call in msg["tool_calls"]:
                        self._execute_tool_call(tool_call)
        else:
            raise Exception(f"Ollama API returned {response.status_code}")

    def _call_gemini(self, prompt, system_prompt):
        if not self.gemini_api_key:
            raise Exception("GEMINI_API_KEY missing from .env")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
        payload = {
            "system_instruction": {"parts": {"text": system_prompt}},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "tools": [
                {
                    "function_declarations": [
                        tool.to_gemini_schema() for tool in self.tools.values()
                    ]
                }
            ],
        }

        response = requests.post(
            url, json=payload, headers={"Content-Type": "application/json"}, timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            if self.chat:
                self.chat.remove_last_message()
            if "candidates" in result and result["candidates"]:
                parts = result["candidates"][0]["content"]["parts"]
                for part in parts:
                    if "text" in part and part["text"]:
                        if self.chat:
                            self.chat.add_message(f"[LLM]: {part['text']}")
                    if "functionCall" in part:
                        fc = part["functionCall"]
                        self._execute_tool_call(
                            {
                                "function": {
                                    "name": fc["name"],
                                    "arguments": fc.get("args", {}),
                                }
                            }
                        )
        else:
            raise Exception(f"Gemini API error: {response.text[:100]}")

    def _execute_tool_call(self, tool_call: Dict):
        func_name = tool_call["function"]["name"]
        if func_name in self.tools:
            args = tool_call["function"].get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)

            if func_name == "say":
                self.tools[func_name].func(args.get("message", ""))
            else:
                self.tools[func_name].func()

            self.memory.append(f"Did: {func_name}")
            if len(self.memory) > self.max_memory:
                self.memory.pop(0)

    def update(self):
        current_time = time.time()
        time_since_decision = current_time - self.last_decision
        time_since_action = current_time - self.last_action_time

        if (
            time_since_decision > self.decision_cooldown
            and time_since_action > self.idle_threshold
            and self.char.action == 0
            and not self.is_thinking
        ):
            self._make_llm_decision(
                "You've been idle for a while. What would you like to do?"
            )
            self.last_decision = current_time

        self.energy = max(0.0, min(1.0, self.energy))


class ChatUI:
    def __init__(self, surface, font_size=18):
        self.surface = surface
        self.font = None
        self.font_size = font_size
        self.messages = []
        self.input_text = ""
        self.max_messages = 12
        self.active = False
        self.chat_height = 150
        self.scroll_offset = 0

    def init_font(self):
        import pygame as pg

        if not self.font:
            pg.font.init()
            self.font = pg.font.Font(None, self.font_size)

    def add_message(self, text: str):
        max_chars = 90
        if len(text) > max_chars:
            words = text.split(" ")
            current_line = ""
            for word in words:
                if len(current_line + word) < max_chars:
                    current_line += word + " "
                else:
                    if current_line:
                        self.messages.append(current_line.strip())
                    current_line = word + " "
            if current_line:
                self.messages.append(current_line.strip())
        else:
            self.messages.append(text)

        if len(self.messages) > self.max_messages:
            self.scroll_offset = len(self.messages) - self.max_messages

    def remove_last_message(self):
        if self.messages:
            self.messages.pop()

    def handle_event(self, event):
        import pygame as pg

        if event.type == pg.KEYDOWN:
            if event.key == pg.K_RETURN:
                if self.input_text.strip():
                    message = self.input_text.strip()
                    self.input_text = ""
                    self.add_message(f"You: {message}")
                    return message
                self.input_text = ""
            elif event.key == pg.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif (
                event.key == pg.K_t
                and not self.active
                and not (pg.key.get_mods() & pg.KMOD_CTRL)
            ):
                self.active = True
                return None
            elif event.key == pg.K_ESCAPE:
                self.active = False
                self.input_text = ""
            elif event.key == pg.K_UP and self.active:
                self.scroll_offset = max(0, self.scroll_offset - 1)
            elif event.key == pg.K_DOWN and self.active:
                max_scroll = max(0, len(self.messages) - self.max_messages)
                self.scroll_offset = min(max_scroll, self.scroll_offset + 1)
            else:
                if self.active and len(self.input_text) < 80:
                    if (
                        event.unicode
                        and event.unicode.isprintable()
                        and event.key != pg.K_RETURN
                    ):
                        self.input_text += event.unicode
        return None

    def draw(self):
        if not self.font:
            self.init_font()
        if not self.font:
            return

        import pygame as pg

        surface_height = self.surface.get_height()
        chat_y = surface_height - self.chat_height

        # UI Styling Refinement
        bg_rect = pg.Rect(0, chat_y, self.surface.get_width(), self.chat_height)
        s = pg.Surface((bg_rect.width, bg_rect.height), pg.SRCALPHA)
        s.fill((20, 20, 20, 210))
        self.surface.blit(s, (0, chat_y))
        pg.draw.rect(self.surface, (60, 60, 60), bg_rect, 2)

        line_height = 20
        visible_lines = (self.chat_height - 35) // line_height
        start_idx = max(0, len(self.messages) - visible_lines + self.scroll_offset)
        end_idx = start_idx + visible_lines
        visible_messages = self.messages[start_idx:end_idx]

        y = chat_y + 8
        for msg in visible_messages:
            color = (230, 230, 230)
            if msg.startswith("WhiteCar:"):
                color = (150, 255, 150)
            elif msg.startswith("You:"):
                color = (150, 200, 255)
            elif msg.startswith("[LLM"):
                color = (255, 180, 100)

            text_surf = self.font.render(msg, True, color)
            self.surface.blit(text_surf, (10, y))
            y += line_height

        input_y = surface_height - 30
        input_bg = pg.Rect(0, input_y, self.surface.get_width(), 30)
        pg.draw.rect(self.surface, (40, 40, 40), input_bg)
        pg.draw.line(
            self.surface,
            (80, 80, 80),
            (0, input_y),
            (self.surface.get_width(), input_y),
            1,
        )

        if self.active:
            # Flashing cursor effect
            cursor = "_" if time.time() % 1.0 < 0.5 else " "
            prompt = f"> {self.input_text}{cursor}"
            color = (255, 255, 150)
        else:
            prompt = "Press 'T' to chat"
            color = (120, 120, 120)

        input_surf = self.font.render(prompt, True, color)
        self.surface.blit(input_surf, (10, input_y + 7))

        if len(self.messages) > visible_lines:
            scroll_text = f"↑↓ {start_idx + 1}-{min(end_idx, len(self.messages))}/{len(self.messages)}"
            scroll_surf = self.font.render(scroll_text, True, (100, 100, 100))
            scroll_x = self.surface.get_width() - scroll_surf.get_width() - 10
            self.surface.blit(scroll_surf, (scroll_x, chat_y + 8))
