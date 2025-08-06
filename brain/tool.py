from typing import Callable, Dict
import json

class Tool:
    def __init__(self, name:str, func:Callable, desc:str, params:Dict):
        self.name, self.func, self.desc = name, func, desc
        self.params = params or {}
    @property
    def schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.desc,
                "parameters": self.params or {"type": "object", "properties": {}}
            }
        }

class ToolExecutor:
    def __init__(self, actor):
        self.actor = actor
    def __call__(self, tool):
        fxn_name = tool["function"]["name"]
        fxn_args = tool["function"].get("arguments", {})
        if isinstance(fxn_args, str):
            fxn_args = json.loads(fxn_args)
        fxn = getattr(self.actor, fxn_name)
        return fxn(**fxn_args)

