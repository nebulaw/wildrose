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

        self.seen_message_ids = set()

        # Message queue to never drop user inputs if AI is currently thinking
        self.message_queue = []

        # Only warn if explicitly missing API key and using Gemini
        if self.provider == "gemini" and not self.gemini_api_key:
            if self.chat:
                self.chat.add_message(
                    "GEMINI_API_KEY is empty! Please check ~/.wildrose/config.json",
                    "error",
                )

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
            messages = state["messages"]

            # 1. Dynamic system prompt injected at runtime (always fresh memory)
            sys_msg = SystemMessage(content=self._get_context())

            # 2. Strip ALL existing SystemMessages from state (cleaning up old migrations)
            to_remove = [
                RemoveMessage(id=m.id)
                for m in messages
                if getattr(m, "type", "") == "system"
            ]
            clean_messages = [m for m in messages if getattr(m, "type", "") != "system"]

            # 3. Truncate context if it gets too long
            if len(clean_messages) > 15:
                keep_from = len(clean_messages) - 10

                # Ensure we start the context window on a HumanMessage to prevent breaking role order/tool pairs
                while (
                    keep_from < len(clean_messages)
                    and getattr(clean_messages[keep_from], "type", "") != "human"
                ):
                    keep_from += 1

                if keep_from == len(clean_messages):
                    keep_from = len(clean_messages) - 2

                # Add truncated old messages to the removal list
                to_remove.extend(
                    [RemoveMessage(id=m.id) for m in clean_messages[:keep_from]]
                )
                clean_messages = clean_messages[keep_from:]

            # 4. Invoke LLM with SystemPrompt + Cleaned History
            invoke_msgs = [sys_msg] + clean_messages
            response = model_with_tools.invoke(invoke_msgs)

            return {"messages": to_remove + [response]}

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
        # Note: We do NOT use self.chat.add_message here anymore!
        # Because LangGraph returns the full AIMessage text at the end of the chain,
        # if we add the message here, it prints once during the tool call,
        # and then the `_llm_worker` loop prints it again, causing duplicates.
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
        self.message_queue.append(f"User said: '{message}'. How do you respond?")
        self._pump_queue()

    def _pump_queue(self):
        if self.is_thinking or not self.message_queue:
            return

        prompt = self.message_queue.pop(0)
        self._make_llm_decision(prompt)

    def _make_llm_decision(self, context: str | None = None):
        if self.is_thinking:
            return
        self.is_thinking = True

        prompt = context or "*You are feeling bored. What do you do?*"

        if self.chat:
            self.chat.set_typing(True)

        threading.Thread(target=self._llm_worker, args=(prompt,), daemon=True).start()

    def _llm_worker(self, prompt: str):
        try:
            # We ONLY send the HumanMessage.
            # The system prompt is dynamically injected by the call_model node.
            inputs = {"messages": [HumanMessage(content=prompt)]}

            res = self.graph.invoke(inputs, self.config)

            if self.chat:
                self.chat.set_typing(False)

            # Extract ALL new messages that we haven't seen before
            for msg in res["messages"]:
                if msg.id not in self.seen_message_ids:
                    self.seen_message_ids.add(msg.id)
                    if isinstance(msg, AIMessage) and msg.content:
                        # Do not display intermediate thought messages if they are just executing a tool
                        # Often Gemini returns an AIMessage with content="" and tool_calls=[...]
                        # Sometimes it returns content="Let me check" and tool_calls=[...].
                        # To prevent duplicate/annoying inner thoughts, we only display it
                        # if it's the final answer (no tool calls) OR we just accept we only want the final message.
                        # Wait, we can just check if tool_calls is empty.
                        if not hasattr(msg, "tool_calls") or not msg.tool_calls:
                            if self.chat:
                                self.chat.add_message(f"{msg.content}", "eve")
                    elif isinstance(msg, ToolMessage):
                        # Tool execution results
                        pass

        except Exception as e:
            if self.chat:
                self.chat.set_typing(False)
                self.chat.add_message(f"LLM Error: {str(e)[:100]}...", "error")
            self._idle()
        finally:
            if self.chat:
                self.chat.set_typing(False)
            self.is_thinking = False
            self.last_decision = time.time()

            # Continue processing queued messages if any exist
            if self.message_queue:
                self._pump_queue()

    def update(self):
        current_time = time.time()
        time_since_decision = current_time - self.last_decision
        time_since_action = current_time - self.last_action_time

        if (
            time_since_decision > self.decision_cooldown
            and time_since_action > self.idle_threshold
            and self.char.action == 0
            and not self.is_thinking
            and not self.message_queue
        ):
            self._make_llm_decision()
            self.last_decision = current_time

        self.energy = max(0.0, min(1.0, self.energy))
