from typing import List

from .context import ContextManager
from .tool import Tool

class Brain:
    def __init__(self, configuration: str):
        self.tools = self._init_tools()
        self.ctx_manager = ContextManager(configuration, self.tools)

    def _init_tools(self) -> List[Tool]:
        # TODO: add tools
        return []
