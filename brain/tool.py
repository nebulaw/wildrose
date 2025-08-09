from typing import Callable, Dict, List
import json

class Tool:
    def __init__(self, name:str, func:Callable, desc:str, params:Dict={}):
        self.name, self.func, self.desc = name, func, desc
        self.params = params
    def __repr__(self): return f"{self.name=}, {self.desc=}, {self.params=}"
    @property
    def schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.desc,
                "parameters": self.params
            }
        }

class ToolExecutor:
    def __init__(self, actor, tools:List[Tool]):
        self.actor = actor
        self.tools = tools
    def __call__(self, tools: List[Dict]):
        ret_vals = []
        for tool in tools:
            fxn_name = tool["function"]["name"]
            fxn_args = tool["function"].get("arguments", {})
            if isinstance(fxn_args, str):
                fxn_args = json.loads(fxn_args)
            fxn = getattr(self.actor, fxn_name)
            ret_vals.append(fxn(**fxn_args))
        return ret_vals
