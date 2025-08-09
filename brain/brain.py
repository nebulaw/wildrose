from typing import List

from .context import ContextManager
from .tool import Tool, ToolExecutor
from .module import Module

class Brain(Module):
    def __init__(self, actor, config: str, tools: List[Tool]):
        self.actor = actor
        self.tools = tools
        self.ctx_manager = ContextManager(config, self.tools)
        self.tool_executor = ToolExecutor(actor, self.tools)
    def __call__(self, msg:str):
        response = self.ctx_manager.send(msg)
        return response["message"], self.tool_executor(response["tool_calls"])
