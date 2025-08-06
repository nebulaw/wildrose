import re

def remove_tag_from_msg(msg:str, tag:str) -> str: return re.sub(rf"<{tag}.*?>.*?</{tag}>", "", msg, flags=re.DOTALL).strip()
