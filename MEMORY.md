# ⚠️ VERY IMPORTANT: SYSTEM STATE & MEMORY ⚠️

**THIS MEMORY FILE IS THE CORE OF ALL SESSIONS.** 
**It requires a mandatory revisit on each step/prompt to be read and updated.** 
**It tracks the absolute state of the session, the project architecture, and the roadmap.** 
**Always refer to this file to understand context, to prevent regressions, and to ensure smooth session compaction for better AI performance.**

---

## 1. Project Overview
**Wildrose** is an interactive, desktop-based 2D pixel game/companion app featuring "Eve" (a virtual white cat). The goal is to provide a serene, interactive companion that learns and acts proactively using modern LLMs.

## 2. Architecture & System Design
The system has been heavily refactored from a raw prototype into a scalable, production-ready desktop application.

*   **Game Engine:** `pygame-ce` (Community Edition). Chosen over standard `pygame` for modern Python (3.14+) compatibility, specifically for reliable Font and Mixer module support.
*   **AI Brain:** `LangGraph` and `LangChain`. Replaced raw HTTP requests to allow for scalable agentic workflows, dynamic tool binding, and robust state management.
    *   Supports both `langchain-google-genai` (Gemini) and `langchain-ollama` (Local models).
*   **State & Persistence (The `~/.wildrose/` directory):**
    *   **Chat Checkpointing:** Handled via LangGraph's `SqliteSaver` storing to `checkpoints.sqlite`. Preserves conversation across reboots.
    *   **Long-Term Memory:** Handled via `memory.py` saving to `memory.json`. The LLM uses a `save_memory` tool to extract and persist user facts, which are injected into the System Prompt.
    *   **Configuration:** `config.py` managing `config.json` allows persistent API keys and model choices without relying strictly on `.env`.
*   **UI/UX Design:** Custom Pygame UI (`ui.py`).
    *   **Aesthetic:** "The Creative Independent" style. Brutalist, minimalist, light background, sharp borders, and clean sans-serif typography.
    *   **Responsive:** The Pygame window is `RESIZABLE`. The UI uses a flexible bounding box system. The Chat is pinned to the left (max width 400px), and the character is centered dynamically on the right using a `pygame.Surface.subsurface`.
    *   **Features:** Word-wrapping, multi-line input (`Shift+Enter`), kinetic scrolling (`MOUSEWHEEL`), and clipboard pasting (`Ctrl+V`).

## 3. Experience & Technical Gotchas (Do Not Repeat Mistakes)
*   **Blocking the Main Loop:** LLM network calls *must* be executed in a background `threading.Thread`. If run on the main thread, the Pygame event loop freezes, and the OS marks the app as "Not Responding".
*   **Context Window Overflow:** Endless chat history breaks LLM token limits and slows down response times. We implemented a manual truncation in LangGraph (`RemoveMessage` for older context) while preserving the System Prompt and the last 10 messages.
*   **Pygame Init Order:** Always initialize `pg.init()` and `pg.font.init()` before trying to render Chat UI text.
*   **Subsurface constraints:** When rendering the character, checking if the window width is larger than the chat width is necessary before attempting to create a right-side subsurface, otherwise Pygame throws a ValueError.

## 4. Implemented Features (Log)
*   [x] Basic character rendering and idle/petting animations.
*   [x] LangGraph integration with Gemini/Ollama tool calling.
*   [x] Asynchronous LLM processing.
*   [x] Responsive Brutalist Chat UI with scrolling and wrapping.
*   [x] SQLite session checkpointing (Short-term memory).
*   [x] JSON-based fact extraction (Long-term memory).

## 5. Next Steps & Roadmap
1.  **Sensory Input Injection:** Eve should "feel" what's happening. Feed Pygame events (window resizing, continuous clicking/petting, time since last interaction) directly into the LangGraph state so she can react to environmental changes.
2.  **Advanced Proactivity:** The current proactivity loop is a simple timer (`idle_threshold`). It should be enhanced to use an "Energy/Boredom" metric, deciding whether to sleep, wander, or initiate a conversation based on the user's long-term memory.
3.  **Animation Polish:** Expand the character sprite interactions, tying specific emotions from the LLM directly to visual state changes.
4.  **Error Recovery:** Make the AI gracefully handle API rate limits without spamming the chat.