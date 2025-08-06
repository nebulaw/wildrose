import requests
import json
from brain.helpers import remove_tag_from_msg
from brain.tool import Tool

OLLAMA_URL="http://localhost:11434/api/chat"
MODEL="deepseek-r1:1.5b"

class ContextManager:
    def __init__(self, config: str, tools: list[Tool]):
        self._tools = tools
        self._context = [{"role": "system", "content": config}]
    @property
    def context(self): return self._context
    def clear(self): self._context.clear()
    def send(self, msg: str, role="user"):
        self._context.append({"role": role, "content": msg})
        r = requests.post(OLLAMA_URL, json={"model": MODEL, "messages": self.context, "stream": False, "tools": self._tools})
        if r.status_code != 200 or "message" not in (result := r.json()): return None
        msg, ret = result["message"], {}
        if "content" in msg:
            ret["message"] = remove_tag_from_msg(msg["content"], "think")
            self._context.append({"role": "assistant", "content": ret["message"]})
        if "tool_calls" in msg: ret["tool_calls"] = msg["tool_calls"]
        return ret
