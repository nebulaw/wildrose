import json
from pathlib import Path
from config import MEMORY_FILE, CONFIG_DIR

class LongTermMemory:
    def __init__(self):
        self._ensure_dir()
        self.facts = []
        self.load()

    def _ensure_dir(self):
        if not CONFIG_DIR.exists():
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def load(self):
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r") as f:
                    self.facts = json.load(f)
            except Exception as e:
                print(f"Error loading memory: {e}")
        else:
            self.save()

    def save(self):
        self._ensure_dir()
        try:
            with open(MEMORY_FILE, "w") as f:
                json.dump(self.facts, f, indent=4)
        except Exception as e:
            print(f"Error saving memory: {e}")

    def add_fact(self, fact: str):
        if fact not in self.facts:
            self.facts.append(fact)
            self.save()

    def get_all(self):
        return self.facts

memory = LongTermMemory()
