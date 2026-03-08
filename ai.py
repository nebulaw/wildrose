import os
import time
import threading
from typing import Callable, Dict, Any, List, Annotated

# Langgraph imports
from typing_extensions import TypedDict
from langchain_core.tools import StructuredTool
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from characters.character import ST_IDLE, ST_RUN, ST_RUSH, ST_DAMAGE, ST_DIE


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

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

class LLMBrain:
    def __init__(self, character, chat_handler=None):
        self.char = character
        self.chat = chat_handler
        self.energy = 1.0
        self.mood = "neutral"
        self.memory = []
        self.max_memory = 5
        self.last_decision = time.time()
        self.last_action_time = time.time()
        self.idle_threshold = 15.0
        self.decision_cooldown = 20.0

        self.provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.is_thinking = False

        self.tools = self._init_tools()
        
        # Init LangGraph
        self.graph = self._build_graph()

        # Initial greeting and status
        if self.chat:
            self.chat.add_message(
                f"[System]: LangGraph initialized via '{self.provider}'"
            )
            if self.provider == "gemini" and not self.gemini_api_key:
                self.chat.add_message("[System Warning]: GEMINI_API_KEY is empty!")
            elif self.provider == "ollama":
                model = os.getenv("OLLAMA_MODEL", "mistral:7b")
                self.chat.add_message(f"[System]: Ollama model set to '{model}'")

        self._make_llm_decision("The user just opened the application. Greet them happily in one short sentence!")

    def _init_tools(self) -> list[StructuredTool]:
        return [
            StructuredTool.from_function(self._move_right, name="move_right", description="Move the cat to the right with rush animation"),
            StructuredTool.from_function(self._idle, name="idle", description="Make the cat return to idle/resting state"),
            StructuredTool.from_function(self._purr, name="purr", description="Make the cat purr contentedly"),
            StructuredTool.from_function(self._meow, name="meow", description="Make the cat meow"),
            StructuredTool.from_function(self._run, name="run", description="Make the cat run in place"),
            StructuredTool.from_function(self._say, name="say", description="Send a message to the user"),
        ]

    def _build_graph(self):
        if self.provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=self.gemini_api_key)
        else:
            from langchain_ollama import ChatOllama
            model = ChatOllama(model=os.getenv("OLLAMA_MODEL", "mistral:7b"))

        model_with_tools = model.bind_tools(self.tools)
        tool_node = ToolNode(self.tools)

        def call_model(state: State):
            return {"messages": [model_with_tools.invoke(state["messages"])]}

        def should_continue(state: State):
            last_message = state["messages"][-1]
            if not last_message.tool_calls:
                return END
            return "tools"

        workflow = StateGraph(State)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")

        return workflow.compile()

    def _move_right(self):
        self.char.set_action(ST_RUSH)
        self.energy -= 0.1
        self.last_action_time = time.time()
        return "Moved right"

    def _idle(self):
        self.char.set_action(ST_IDLE)
        self.energy += 0.05
        self.last_action_time = time.time()
        return "Idling"

    def _purr(self):
        self.char.purr()
        self.mood = "happy"
        self.last_action_time = time.time()
        return "Purring"

    def _meow(self):
        self.char.meow()
        self.last_action_time = time.time()
        return "Meowing"

    def _run(self):
        self.char.set_action(ST_RUN)
        self.energy -= 0.15
        self.last_action_time = time.time()
        return "Running"

    def _say(self, message: str):
        if self.chat:
            self.chat.add_message(f"WhiteCar: {message}")
        return f"Said: {message}"

    def _get_context(self) -> str:
        return f"""You are WhiteCar, a cute virtual cat. Current status:
- Energy: {self.energy:.1f}/1.0
- Mood: {self.mood}
- Recent memories: {self.memory[-3:] if self.memory else "none"}

You can move around, make sounds, and chat with the user. Be playful and cat-like! Keep responses very short."""

    def process_user_message(self, message: str):
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

        threading.Thread(
            target=self._llm_worker, args=(prompt, system_prompt), daemon=True
        ).start()

    def _llm_worker(self, prompt: str, system_prompt: str):
        try:
            inputs = {"messages": [SystemMessage(content=system_prompt), HumanMessage(content=prompt)]}
            res = self.graph.invoke(inputs)
            
            if self.chat:
                self.chat.remove_last_message()

            for msg in res["messages"]:
                if isinstance(msg, AIMessage) and msg.content:
                    if self.chat:
                        self.chat.add_message(f"[LLM]: {msg.content}")
                elif isinstance(msg, ToolMessage):
                    self.memory.append(f"Did: {msg.name}")
                    if len(self.memory) > self.max_memory:
                        self.memory.pop(0)

        except Exception as e:
            if self.chat:
                self.chat.remove_last_message()
                self.chat.add_message(f"[LLM Error]: {str(e)[:50]}...")
            self._idle()
        finally:
            self.is_thinking = False

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
    def __init__(self, surface, font_size=16):
        self.surface = surface
        self.font = None
        self.font_size = font_size
        self.messages = []
        self.input_text = ""
        self.max_messages = 30
        self.active = False
        self.scroll_offset = 0

    def init_font(self):
        import pygame as pg

        if not self.font:
            pg.font.init()
            # Try to use a clean modern font
            try:
                self.font = pg.font.SysFont("helvetica", self.font_size)
            except:
                self.font = pg.font.Font(None, self.font_size)

    def add_message(self, text: str):
        max_chars = 40 # Narrow sidebar
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

    def draw(self, rect=None):
        if not self.font:
            self.init_font()
        if not self.font:
            return

        import pygame as pg

        if rect is None:
            chat_x, chat_y, chat_w, chat_h = 0, 0, self.surface.get_width(), self.surface.get_height()
        else:
            chat_x, chat_y, chat_w, chat_h = rect.x, rect.y, rect.width, rect.height

        # Minimalist light brutalist background (like creative independent)
        bg_rect = pg.Rect(chat_x, chat_y, chat_w, chat_h)
        pg.draw.rect(self.surface, (250, 250, 250), bg_rect)
        # Separator line on the right
        pg.draw.line(self.surface, (0, 0, 0), (chat_x + chat_w - 1, chat_y), (chat_x + chat_w - 1, chat_y + chat_h), 2)

        input_h = 40
        input_y = chat_y + chat_h - input_h
        pg.draw.line(self.surface, (0, 0, 0), (chat_x, input_y), (chat_x + chat_w, input_y), 1)

        line_height = 20
        visible_lines = (chat_h - input_h - 10) // line_height
        start_idx = max(0, len(self.messages) - visible_lines + self.scroll_offset)
        end_idx = start_idx + visible_lines
        visible_messages = self.messages[start_idx:end_idx]

        y = chat_y + 10
        for msg in visible_messages:
            color = (0, 0, 0) # default black
            if msg.startswith("WhiteCar:"):
                color = (30, 130, 50)
            elif msg.startswith("You:"):
                color = (50, 50, 200)
            elif msg.startswith("[LLM"):
                color = (180, 100, 0)

            text_surf = self.font.render(msg, True, color)
            self.surface.blit(text_surf, (chat_x + 10, y))
            y += line_height

        if self.active:
            cursor = "_" if time.time() % 1.0 < 0.5 else " "
            prompt = f"> {self.input_text}{cursor}"
            color = (0, 0, 0)
        else:
            prompt = "Press 'T' to chat"
            color = (150, 150, 150)

        input_surf = self.font.render(prompt, True, color)
        self.surface.blit(input_surf, (chat_x + 10, input_y + 12))
