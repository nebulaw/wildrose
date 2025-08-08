import json
import time
import requests
from typing import Callable, Dict, Any, List
from characters.character import ST_IDLE, ST_RUN, ST_RUSH, ST_DAMAGE, ST_DIE

class Tool:
    def __init__(self, name: str, func: Callable, desc: str, params: Dict = None):
        self.name, self.func, self.desc = name, func, desc
        self.params = params or {}
    
    def to_schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.desc,
                "parameters": self.params or {"type": "object", "properties": {}}
            }
        }

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
        self.idle_threshold = 15.0  # 15 seconds of idling before LLM decision
        self.decision_cooldown = 20.0  # 20 seconds between autonomous decisions
        
    def _init_tools(self) -> Dict[str, Tool]:
        return {
            "move_right": Tool("move_right", self._move_right, "Move the cat to the right with rush animation"),
            "idle": Tool("idle", self._idle, "Make the cat return to idle/resting state"),
            "purr": Tool("purr", self._purr, "Make the cat purr contentedly"),
            "meow": Tool("meow", self._meow, "Make the cat meow"),
            "run": Tool("run", self._run, "Make the cat run in place"),
            "say": Tool("say", self._say, "Send a message to the user", {
                "type": "object",
                "properties": {"message": {"type": "string", "description": "Message to send"}},
                "required": ["message"]
            }),
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
- Recent memories: {self.memory[-3:] if self.memory else 'none'}

You can move around, make sounds, and chat with the user. Be playful and cat-like!"""
    
    def process_user_message(self, message: str):
        """Handle direct user messages"""
        self.memory.append(f"User said: {message}")
        if len(self.memory) > self.max_memory:
            self.memory.pop(0)
        
        # Make LLM decision about how to respond
        self._make_llm_decision(f"User said: '{message}'. How do you respond?")
    
    def _make_llm_decision(self, context: str = None):
        """Use Ollama to make decisions with streaming"""
        try:
            prompt = context or "What would you like to do next?"
            system_prompt = self._get_context()
            
            if self.chat:
                self.chat.add_message("[LLM thinking...]")
            
            response = requests.post('http://localhost:11434/api/chat', json={
                "model": "mistral:7b",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "tools": [tool.to_schema() for tool in self.tools.values()],
                "stream": False
            }, timeout=5)
            
            if response.status_code == 200:
                result = response.json()
                if self.chat:
                    self.chat.remove_last_message()  # Remove thinking message
                    
                if 'message' in result:
                    # Log LLM response
                    if 'content' in result['message'] and result['message']['content']:
                        if self.chat:
                            self.chat.add_message(f"[LLM]: {result['message']['content']}")
                    
                    if 'tool_calls' in result['message']:
                        for tool_call in result['message']['tool_calls']:
                            self._execute_tool_call(tool_call)
                        
        except Exception as e:
            if self.chat:
                self.chat.remove_last_message()  # Remove thinking message
                self.chat.add_message(f"[LLM Error]: {str(e)}")
            self._idle()
    
    def _execute_tool_call(self, tool_call: Dict):
        """Execute a tool call from the LLM"""
        func_name = tool_call['function']['name']
        if func_name in self.tools:
            args = tool_call['function'].get('arguments', {})
            if isinstance(args, str):
                args = json.loads(args)
            
            if func_name == "say":
                self.tools[func_name].func(args.get('message', ''))
            else:
                self.tools[func_name].func()
                
            self.memory.append(f"Did: {func_name}")
            if len(self.memory) > self.max_memory:
                self.memory.pop(0)
    
    def update(self):
        """Autonomous behavior updates - only when idling"""
        current_time = time.time()
        
        # Only make autonomous decisions if:
        # 1. Enough time has passed since last decision
        # 2. Cat has been idle for the threshold time
        # 3. Character is currently in idle state
        time_since_decision = current_time - self.last_decision
        time_since_action = current_time - self.last_action_time
        
        if (time_since_decision > self.decision_cooldown and 
            time_since_action > self.idle_threshold and
            self.char.action == 0):  # ST_IDLE = 0
            
            self._make_llm_decision("You've been idle for a while. What would you like to do?")
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
        # Split long messages into multiple lines
        max_chars = 90
        if len(text) > max_chars:
            words = text.split(' ')
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
        
        # Auto-scroll to bottom when new message arrives
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
                    self.input_text = ""  # Clear input immediately
                    return message
                self.input_text = ""
            elif event.key == pg.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.key == pg.K_t and not self.active:
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
                    self.input_text += event.unicode
        return None
    
    def draw(self):
        if not self.font:
            self.init_font()
            
        import pygame as pg
        
        # Position chat at bottom
        surface_height = self.surface.get_height()
        chat_y = surface_height - self.chat_height
        
        # Draw chat background (always visible)
        bg_rect = pg.Rect(0, chat_y, self.surface.get_width(), self.chat_height)
        pg.draw.rect(self.surface, (20, 20, 20, 200), bg_rect)
        pg.draw.rect(self.surface, (100, 100, 100), bg_rect, 2)
        
        # Calculate visible messages
        line_height = 20
        visible_lines = (self.chat_height - 30) // line_height
        start_idx = max(0, len(self.messages) - visible_lines + self.scroll_offset)
        end_idx = start_idx + visible_lines
        visible_messages = self.messages[start_idx:end_idx]
        
        # Draw messages
        y = chat_y + 5
        for msg in visible_messages:
            # Color code different message types
            color = (255, 255, 255)
            if msg.startswith("WhiteCar:"):
                color = (150, 255, 150)
            elif msg.startswith("You:"):
                color = (150, 150, 255)
            elif msg.startswith("[LLM"):
                color = (255, 200, 100)
            
            text_surf = self.font.render(msg, True, color)
            self.surface.blit(text_surf, (5, y))
            y += line_height
        
        # Draw input area
        input_y = surface_height - 25
        input_bg = pg.Rect(0, input_y, self.surface.get_width(), 25)
        pg.draw.rect(self.surface, (40, 40, 40), input_bg)
        
        if self.active:
            prompt = f"> {self.input_text}_"
            color = (255, 255, 100)
        else:
            prompt = "Press 'T' to chat"
            color = (150, 150, 150)
            
        input_surf = self.font.render(prompt, True, color)
        self.surface.blit(input_surf, (5, input_y + 5))
        
        # Show scroll indicator
        if len(self.messages) > visible_lines:
            scroll_text = f"↑↓ {start_idx + 1}-{min(end_idx, len(self.messages))}/{len(self.messages)}"
            scroll_surf = self.font.render(scroll_text, True, (100, 100, 100))
            scroll_x = self.surface.get_width() - scroll_surf.get_width() - 5
            self.surface.blit(scroll_surf, (scroll_x, chat_y + 5))