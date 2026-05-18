import asyncio
import re
import threading
import json
import sys
import traceback
import os
from pathlib import Path

import sounddevice as sd
from google import genai
from google.genai import types
from ui import JarvisUI
from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
)

from actions.file_processor import file_processor
from actions.flight_finder     import flight_finder
from actions.open_app          import open_app
from actions.weather_report    import weather_action
from actions.send_message      import send_message
from actions.reminder          import reminder
from actions.computer_settings import computer_settings
from actions.screen_processor  import screen_process
from actions.youtube_video     import youtube_video
from actions.desktop           import desktop_control
from actions.browser_control   import browser_control
from actions.file_controller   import file_controller
from actions.code_helper       import code_helper
from actions.dev_agent         import dev_agent
from actions.web_search        import web_search as web_search_action
from actions.computer_control  import computer_control
from actions.game_updater      import game_updater

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Platform-aware imports (Windows-specific)
if sys.platform == 'win32':
    try:
        import pycaw
        from comtypes import CLSCTX_ALL
    except ImportError:
        pass
    try:
        from win10toast import ToastNotifier
    except ImportError:
        pass
    try:
        from pywinauto import Desktop
    except ImportError:
        pass


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
LIVE_MODEL          = "models/gemini-2.5-flash-native-audio-preview-12-2025"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024

def _get_api_key() -> str:
    """
    Get API key from .env file first, then fallback to config/api_keys.json for backward compatibility.
    This avoids storing sensitive credentials in plain text.
    """
    # Try .env file first (recommended)
    api_key = os.getenv('GOOGLE_API_KEY')
    if api_key:
        return api_key
    
    # Fallback to config/api_keys.json for backward compatibility
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)["gemini_api_key"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        raise RuntimeError(
            f"API key not found. Please either:\n"
            f"1. Create a .env file with: GOOGLE_API_KEY=your_key_here\n"
            f"2. Or use the GUI to set it up (stores in {API_CONFIG_PATH})"
        )


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are JARVIS, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )

_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

def _clean_transcript(text: str) -> str:    
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()