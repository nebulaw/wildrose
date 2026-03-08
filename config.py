import os
import json
from pathlib import Path

# Use a global hidden directory in the user's home folder
CONFIG_DIR = Path.home() / ".wildrose"
CONFIG_FILE = CONFIG_DIR / "config.json"
MEMORY_FILE = CONFIG_DIR / "memory.json"

DEFAULT_CONFIG = {
    "llm_provider": "gemini",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.5-flash",
    "ollama_model": "mistral:7b",
    "theme": "light"
}

class ConfigManager:
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self._ensure_dir()
        self.load()
        # Also load from local .env to allow project-specific overrides during dev
        self._load_env()

    def _ensure_dir(self):
        if not CONFIG_DIR.exists():
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    user_config = json.load(f)
                    self.config.update(user_config)
            except Exception as e:
                print(f"Error loading config: {e}")
        else:
            self.save()

    def save(self):
        self._ensure_dir()
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _load_env(self):
        try:
            with open(".env") as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        k, v = line.strip().split("=", 1)
                        k = k.lower()
                        if k in self.config:
                            self.config[k] = v
        except FileNotFoundError:
            pass

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def set(self, key: str, value):
        self.config[key] = value
        self.save()

config = ConfigManager()
