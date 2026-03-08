import os
import time
import threading
import sqlite3
from typing import Callable, Dict, Any, List, Annotated

# Langgraph imports
from typing_extensions import TypedDict
from langchain_core.tools import StructuredTool
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    AIMessage,
    ToolMessage,
    RemoveMessage,
)
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver

# Wildrose imports
from characters.character import ST_IDLE, ST_RUN, ST_RUSH, ST_DAMAGE, ST_DIE
from config import config, CONFIG_DIR
from memory import memory


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class LLMBrain:
    def __init__(self, character, chat_handler=None):
        self.char = character
        self.chat = chat_handler
        self.energy = 1.0
        self.mood = "neutral"

        self.max_memory = 5
        self.last_decision = time.time()
        self.last_action_time = time.time()
        self.idle_threshold = 15.0
        self.decision_cooldown = 20.0

        self.provider = config.get("llm_provider", "ollama").lower()
        self.gemini_api_key = config.get("gemini_api_key", "")
        self.is_thinking = False

        self.tools = self._init_tools()

        # Init LangGraph
        self.graph = self._build_graph()
        self.thread_id = "wildrose_user"
        self.config = {"configurable": {"thread_id": self.thread_id}}

        # Initial greeting and status
        if self.chat:
            self.chat.add_message(f"AI initialized via '{self.provider}'", "system")
            if self.provider == "gemini" and not self.gemini_api_key:
                self.chat.add_message(
                    "GEMINI_API_KEY is empty! Please check ~/.wildrose/config.json",
                    "error",
                )
            elif self.provider == "ollama":
                model = config.get("ollama_model", "mistral:7b")
                self.chat.add_message(f"Ollama model set to '{model}'", "system")

        # Start background check for initial greeting without locking main thread
        threading.Thread(target=self._initial_greet, daemon=True).start()

    def _initial_greet(self):
        # We check if there's any state (existing chat history)
        # If there isn't, we send the initial prompt.
        try:
            state = self.graph.get_state(self.config)
            if not state.values or not state.values.get("messages"):
                self._make_llm_decision(
                    "The user just opened the application. Greet them happily in one short sentence!"
                )
        except Exception:
            self._make_llm_decision(
                "The user just opened the application. Greet them happily in one short sentence!"
            )

    def _init_tools(self) -> list[StructuredTool]:
        return [
            StructuredTool.from_function(
                self._move_right,
                name="move_right",
                description="Move the cat to the right with rush animation",
            ),
            StructuredTool.from_function(
                self._idle,
                name="idle",
                description="Make the cat return to idle/resting state",
            ),
            StructuredTool.from_function(
                self._purr, name="purr", description="Make the cat purr contentedly"
            ),
            StructuredTool.from_function(
                self._meow, name="meow", description="Make the cat meow"
            ),
            StructuredTool.from_function(
                self._run, name="run", description="Make the cat run in place"
            ),
            StructuredTool.from_function(
                self._say, name="say", description="Send a message to the user"
            ),
            StructuredTool.from_function(
                self._save_memory,
                name="save_memory",
                description="Save an important fact about the user to long-term memory",
            ),
        ]

    def _build_graph(self):
        if self.provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI

            gemini_model = config.get("gemini_model", "gemini-2.5-flash")
            model = ChatGoogleGenerativeAI(
                model=gemini_model, google_api_key=self.gemini_api_key
            )
        else:
            from langchain_ollama import ChatOllama

            model = ChatOllama(model=config.get("ollama_model", "mistral:7b"))

        model_with_tools = model.bind_tools(self.tools)
        tool_node = ToolNode(self.tools)

        def call_model(state: State):
            # Truncate context if it gets too long
            messages = state["messages"]
            if len(messages) > 20:
                # Remove the oldest messages (keep System prompt at 0)
                # Return RemoveMessage objects for everything up to the last 10 messages
                to_remove = [RemoveMessage(id=m.id) for m in messages[1:-10]]
                return {
                    "messages": to_remove + [model_with_tools.invoke(messages[-10:])]
                }

            return {"messages": [model_with_tools.invoke(messages)]}

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

        # Persistent checkpointer
        db_path = CONFIG_DIR / "checkpoints.sqlite"
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        checkpointer = SqliteSaver(self.conn)

        return workflow.compile(checkpointer=checkpointer)

    # ---- Tools ----
    def _save_memory(self, fact: str):
        memory.add_fact(fact)
        return f"Saved fact: {fact}"

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
            self.chat.add_message(message, "eve")
        return f"Said: {message}"

    def _get_context(self) -> str:
        long_term = "\n".join([f"- {fact}" for fact in memory.get_all()])
        return f"""You are WhiteCar, a cute virtual cat companion.

Current internal status:
- Energy: {self.energy:.1f}/1.0
- Mood: {self.mood}

Known facts about the user:
{long_term if long_term else "- None yet"}

Guidelines:
1. You can move around, make sounds, and chat with the user.
2. Be playful, concise, and cat-like! Keep responses very short (1-2 sentences).
3. Always use the 'save_memory' tool if you learn something important about the user.
4. You don't have to always 'say' something. Sometimes just purring or moving is enough.
"""

    def process_user_message(self, message: str):
        self._make_llm_decision(f"User said: '{message}'. How do you respond?")

    def _make_llm_decision(self, context: str | None = None):
        if self.is_thinking:
            return
        self.is_thinking = True

        prompt = context or "*You are feeling bored. What do you do?*"
        system_prompt = self._get_context()

        if self.chat:
            self.chat.add_message("...", "system")

        threading.Thread(
            target=self._llm_worker, args=(prompt, system_prompt), daemon=True
        ).start()

    def _llm_worker(self, prompt: str, system_prompt: str):
        try:
            state = self.graph.get_state(self.config)

            inputs = None
            if not state.values or not state.values.get("messages"):
                # First run
                inputs = {
                    "messages": [
                        SystemMessage(content=system_prompt, id="eve_system_prompt"),
                        HumanMessage(content=prompt),
                    ]
                }
            else:
                # Update system prompt dynamically if needed by overriding the existing ID
                inputs = {
                    "messages": [
                        SystemMessage(content=system_prompt, id="eve_system_prompt"),
                        HumanMessage(content=prompt),
                    ]
                }

            res = self.graph.invoke(inputs, self.config)

            if self.chat:
                self.chat.remove_last_message()

            # The graph response includes ALL messages in state.
            # Find the new messages. A simplistic approach is looking at the last message.
            last_msg = res["messages"][-1]
            if isinstance(last_msg, AIMessage) and last_msg.content:
                if self.chat:
                    self.chat.add_message(f"{last_msg.content}", "eve")
            elif isinstance(last_msg, ToolMessage):
                # We could log tool usage silently
                pass

        except Exception as e:
            if self.chat:
                self.chat.remove_last_message()
                self.chat.add_message(f"LLM Error: {str(e)[:100]}...", "error")
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
            self._make_llm_decision()
            self.last_decision = current_time

        self.energy = max(0.0, min(1.0, self.energy))
