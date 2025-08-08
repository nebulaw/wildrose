from typing import List

from .context import ContextManager
from .tool import Tool

class Brain:
    def __init__(self, consciousness: str, tools: List[Tool]):
        self.tools = tools
        self.ctx_manager = ContextManager(consciousness, self.tools)
