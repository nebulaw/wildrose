from typing import TypedDict, List, Dict, Any
import requests
from brain.helpers import remove_tag_from_msg
from brain.tool import Tool, ToolExecutor

OLLAMA_URL="http://localhost:11434/api/chat"
MODEL="mistral:7b"

class ChatContextResponse(TypedDict):
    message: str = ""
    tool_calls: List[Dict[str, Any]] = []

class ContextManager:
    def __init__(self, config: str, tools: list[Tool]):
        self._tools = tools
        self._context = [{"role": "system", "content": config}]
    @property
    def context(self): return self._context
    def clear(self): self._context.clear()
    def send(self, msg: str, role="user", tools=None) -> ChatContextResponse:
        if not tools: tools = self._tools
        if isinstance(tools, list) and all(isinstance(tool, Tool) for tool in tools):
            tools = [tool.schema for tool in tools]
        self._context.append({"role": role, "content": msg})
        r = requests.post(OLLAMA_URL, json={"model": MODEL, "messages": self.context, "stream": False, "tools": tools})
        if r.status_code != 200 or "message" not in (result := r.json()): return ChatContextResponse()
        msg, ret = result["message"], ChatContextResponse()
        if "content" in msg:
            ret["message"] = remove_tag_from_msg(msg["content"], "think")
            self._context.append({"role": "assistant", "content": ret["message"]})
        if "tool_calls" in msg: ret["tool_calls"] = msg["tool_calls"]
        return ret


if __name__ == "__main__":
    class TestActor:
        @staticmethod
        def hello_user():
            print("You just printed this")
            for i in range(10):
                print(f"HEY {i+1}")

    test_tool = Tool(
        "hello_user",
        TestActor.hello_user,
        "Use only when you need to say hello to the user",
    )

    context = ContextManager(config="You are a helpful assistant", tools=[test_tool])
    executor = ToolExecutor(TestActor, [test_tool])

    while True:
        res = context.send(input("You: "))
        if "tool_calls" in res:
            executor(res["tool_calls"])
        else:
            print(res["message"])
