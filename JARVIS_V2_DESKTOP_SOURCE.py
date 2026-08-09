# ==========================================
# DATT'S JARVIS AI (Version 2 - Extended Multilingual Feature Pack)
# Complete Production Repair - Final Release
# Created by Datt Dave
# ==========================================

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import random
import re
import shutil
import sys
import tempfile
import threading
import time
import urllib.parse
import webbrowser

from datetime import datetime, timedelta

# Suppress noisy startup / backend logs
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")

import edge_tts
import keyboard
import pygame
import requests
import speech_recognition as sr
from groq import Groq

# ---------------------------------------------------------------------------
# Optional Dependencies with Graceful Fallbacks
# ---------------------------------------------------------------------------

try:
    import pywhatkit
    HAS_PYWHATKIT = True
except ImportError:
    HAS_PYWHATKIT = False

try:
    from openwakeword.model import Model as OpenWakeWordModel
    import openwakeword
    import numpy as np
    import pyaudio
    HAS_OPENWAKEWORD = True
except ImportError:
    OpenWakeWordModel = None
    openwakeword = None
    np = None
    pyaudio = None
    HAS_OPENWAKEWORD = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

# ---------------------------------------------------------------------------
# Path & Storage Configurations
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_FOLDER = os.path.join(os.path.expanduser("~"), "Music")
HISTORY_FILE = os.path.join(BASE_DIR, "conversation_history.json")
REMINDERS_FILE = os.path.join(BASE_DIR, "reminders.json")
SHORTCUTS_FILE = os.path.join(BASE_DIR, "shortcuts.json")
MEMORY_FILE = os.path.join(BASE_DIR, "user_memory.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_STT_MODEL = os.environ.get("GROQ_STT_MODEL", "whisper-large-v3")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
DEFAULT_CITY = os.environ.get("DEFAULT_CITY", "Ahmedabad")

WAKE_PHRASES = ("hey jarvis", "hey jar", "ok jarvis", "hello jarvis", "a jarvis")
WAKE_SINGLE_WORDS = frozenset({"jarvis", "jar"})

STOP_COMMANDS = frozenset(
    {
        # English
        "stop", "jarvis stop", "stop speaking", "be quiet", "quiet",
        # Hindi / Hinglish
        "bas", "ruko", "ruk jao", "chup", "band karo", "बंद करो", "रुको", "चुप",
        # Spanish
        "para", "parar", "detente", "silencio", "cállate",
        # French
        "arrête", "arrete", "stop parle", "tais-toi", "silence",
        # German
        "stopp", "halt auf", "ruhe", "sei still",
        # Italian
        "fermati", "basta", "zitto",
        # Portuguese
        "pare", "chega", "calada",
        # Russian
        "стоп", "хватит", "молчи",
        # Arabic
        "توقف", "اسكت", "بس",
        # Chinese
        "停止", "别说了", "闭嘴",
        # Japanese
        "ストップ", "やめて", "静かに",
        # Korean
        "멈춰", "조용히 해", "그만",
        # Bengali
        "থামো", "চুপ করো", "বন্ধ করো",
        # Gujarati
        "ઉભા રહો", "ચુપ", "બંધ કરો",
        # Marathi
        "थांबा", "शांत रहा",
        # Punjabi
        "ਰੁਕੋ", "ਚੁੱਪ",
        # Tamil
        "நிறுத்து", "அமைதியாக இரு",
        # Telugu
        "ఆపు", "నిశ్శబ్దంగా ఉండు",
        # Kannada
        "ನಿಲ್ಲಿಸಿ", "ಮೌನವಾಗಿರಿ",
        # Malayalam
        "നിർത്തൂ", "നിശബ്ദനായിരിക്കൂ",
        # Urdu
        "روكو", "خاموش",
        # Turkish
        "dur", "sus",
        # Dutch
        "stop maar", "zwijg",
        # Polish
        "zatrzymaj", "cisza",
        # Indonesian
        "berhenti", "diam",
    }
)

# ---------------------------------------------------------------------------
# Multilingual System Definitions
# ---------------------------------------------------------------------------

SUPPORTED_LANGUAGES = {
    "en": {"name": "English", "stt_code": "en-IN", "voice": "en-US-JennyNeural"},
    "hi": {"name": "Hindi", "stt_code": "hi-IN", "voice": "hi-IN-SwaraNeural"},
    "es": {"name": "Spanish", "stt_code": "es-ES", "voice": "es-ES-ElviraNeural"},
    "fr": {"name": "French", "stt_code": "fr-FR", "voice": "fr-FR-DeniseNeural"},
    "de": {"name": "German", "stt_code": "de-DE", "voice": "de-DE-KatjaNeural"},
    "it": {"name": "Italian", "stt_code": "it-IT", "voice": "it-IT-ElsaNeural"},
    "pt": {"name": "Portuguese", "stt_code": "pt-BR", "voice": "pt-BR-FranciscaNeural"},
    "ru": {"name": "Russian", "stt_code": "ru-RU", "voice": "ru-RU-SvetlanaNeural"},
    "ar": {"name": "Arabic", "stt_code": "ar-SA", "voice": "ar-SA-ZariyahNeural"},
    "zh": {"name": "Chinese", "stt_code": "zh-CN", "voice": "zh-CN-XiaoxiaoNeural"},
    "ja": {"name": "Japanese", "stt_code": "ja-JP", "voice": "ja-JP-NanamiNeural"},
    "ko": {"name": "Korean", "stt_code": "ko-KR", "voice": "ko-KR-SunHiNeural"},
    "bn": {"name": "Bengali", "stt_code": "bn-IN", "voice": "bn-IN-TanishaaNeural"},
    "pa": {"name": "Punjabi", "stt_code": "pa-IN", "voice": "pa-IN-OjasNeural"},
    "gu": {"name": "Gujarati", "stt_code": "gu-IN", "voice": "gu-IN-DhwaniNeural"},
    "mr": {"name": "Marathi", "stt_code": "mr-IN", "voice": "mr-IN-AarohiNeural"},
    "ta": {"name": "Tamil", "stt_code": "ta-IN", "voice": "ta-IN-PallaviNeural"},
    "te": {"name": "Telugu", "stt_code": "te-IN", "voice": "te-IN-ShrutiNeural"},
    "kn": {"name": "Kannada", "stt_code": "kn-IN", "voice": "kn-IN-SapnaNeural"},
    "ml": {"name": "Malayalam", "stt_code": "ml-IN", "voice": "ml-IN-SobhanaNeural"},
    "ur": {"name": "Urdu", "stt_code": "ur-PK", "voice": "ur-PK-UzmaNeural"},
    "tr": {"name": "Turkish", "stt_code": "tr-TR", "voice": "tr-TR-EmelNeural"},
    "nl": {"name": "Dutch", "stt_code": "nl-NL", "voice": "nl-NL-ColetteNeural"},
    "pl": {"name": "Polish", "stt_code": "pl-PL", "voice": "pl-PL-ZofiaNeural"},
    "id": {"name": "Indonesian", "stt_code": "id-ID", "voice": "id-ID-GadisNeural"},
}

_current_language = "en"
_last_detected_language = "en"

# ---------------------------------------------------------------------------
# Thread-Safe Microphone Resource & Speech Recognition Engine Configuration
# ---------------------------------------------------------------------------

recognizer = sr.Recognizer()
recognizer.dynamic_energy_threshold = True
recognizer.energy_threshold = 300
recognizer.pause_threshold = 0.6
recognizer.non_speaking_duration = 0.3

_mic_calibrated = False
_mic_lock = threading.Lock()

def get_working_microphone() -> sr.Microphone:
    """Safely select and instantiate a working microphone source."""
    try:
        return sr.Microphone()
    except Exception as e:
        logging.warning(f"Default microphone initialization warning: {e}")
        mics = sr.Microphone.list_microphone_names()
        for idx, name in enumerate(mics):
            try:
                return sr.Microphone(device_index=idx)
            except Exception:
                continue
        return sr.Microphone()

# ---------------------------------------------------------------------------
# AI Clients
# ---------------------------------------------------------------------------

_groq_api_key = os.environ.get("GROQ_API_KEY", "")
groq_client = Groq(api_key=_groq_api_key) if _groq_api_key else None

# ---------------------------------------------------------------------------
# Asynchronous Thread Worker for Edge TTS
# ---------------------------------------------------------------------------

class AsyncLoopThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.loop = asyncio.new_event_loop()

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_coroutine(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result()

_async_worker = AsyncLoopThread()
_async_worker.start()

# ---------------------------------------------------------------------------
# Text-to-Speech & Voice Interruption Architecture
# ---------------------------------------------------------------------------

_speech_stop = False
_is_speaking = False
_mixer_ready = False
_tts_lock = threading.Lock()

def _ensure_mixer() -> None:
    global _mixer_ready
    if not _mixer_ready:
        try:
            pygame.mixer.init()
            _mixer_ready = True
        except Exception as e:
            logging.error(f"Pygame mixer initialization error: {e}")

def _detect_text_script_lang(text: str) -> str:
    """Best-effort script detection for text that is already available."""
    for ch in text:
        code = ord(ch)
        if 0x0900 <= code <= 0x097F:
            return _last_detected_language if _last_detected_language in {"hi", "mr"} else "hi"
        if 0x0980 <= code <= 0x09FF:
            return "bn"
        if 0x0A00 <= code <= 0x0A7F:
            return "pa"
        if 0x0A80 <= code <= 0x0AFF:
            return "gu"
        if 0x0B80 <= code <= 0x0BFF:
            return "ta"
        if 0x0C00 <= code <= 0x0C7F:
            return "te"
        if 0x0C80 <= code <= 0x0CFF:
            return "kn"
        if 0x0D00 <= code <= 0x0D7F:
            return "ml"
        if 0x0600 <= code <= 0x06FF:
            return _last_detected_language if _last_detected_language in {"ar", "ur"} else "ar"
        if 0x4E00 <= code <= 0x9FFF:
            return "zh"
        if 0x3040 <= code <= 0x30FF:
            return "ja"
        if 0xAC00 <= code <= 0xD7AF:
            return "ko"
        if 0x0400 <= code <= 0x04FF:
            return "ru"
    return _last_detected_language or _current_language or "en"

def _pick_voice(text: str) -> str:
    lang_code = _last_detected_language or _current_language or "en"
    if lang_code not in SUPPORTED_LANGUAGES:
        lang_code = _detect_text_script_lang(text)
    return SUPPORTED_LANGUAGES.get(lang_code, SUPPORTED_LANGUAGES["en"])["voice"]

def stop_speaking() -> None:
    global _speech_stop
    _speech_stop = True
    try:
        if _mixer_ready:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
    except Exception:
        pass

def _safe_remove(file_path: str) -> None:
    """Safe helper to remove audio file without raising Lock/Permission errors."""
    for _ in range(5):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            break
        except Exception:
            time.sleep(0.1)

async def _edge_tts_speak(text: str) -> None:
    global _speech_stop, _is_speaking

    _speech_stop = False
    _is_speaking = True

    if not text or not text.strip():
        _is_speaking = False
        return

    temp_dir = tempfile.gettempdir()
    temp_voice_file = os.path.join(temp_dir, f"jarvis_tts_{threading.get_ident()}_{int(time.time() * 1000)}.mp3")

    selected_voice = _pick_voice(text)
    fallback_voices = [selected_voice, "en-US-JennyNeural", "hi-IN-SwaraNeural"]

    seen_voices = set()
    unique_voices = [v for v in fallback_voices if not (v in seen_voices or seen_voices.add(v))]

    generated_successfully = False
    for voice in unique_voices:
        try:
            communicate = edge_tts.Communicate(text=text, voice=voice)
            await communicate.save(temp_voice_file)

            if os.path.exists(temp_voice_file) and os.path.getsize(temp_voice_file) > 0:
                generated_successfully = True
                break
        except Exception as exc:
            logging.warning(f"Edge TTS synthesis warning (Voice: {voice}): {exc}")
            _safe_remove(temp_voice_file)

    if not generated_successfully:
        logging.error("TTS error: No audio was received from Edge TTS after trying fallbacks.")
        _is_speaking = False
        return

    _ensure_mixer()
    try:
        pygame.mixer.music.load(temp_voice_file)
        pygame.mixer.music.play()
    except Exception as exc:
        logging.error(f"Audio Playback error: {exc}")
        _is_speaking = False
        _safe_remove(temp_voice_file)
        return

    def _barge_in_listener():
        """Persistent microphone listener for voice barge-in / stop command."""
        if not _mic_lock.acquire(blocking=False):
            return
        try:
            with get_working_microphone() as source:
                while _mixer_ready and pygame.mixer.music.get_busy() and not _speech_stop:
                    try:
                        audio = recognizer.listen(source, timeout=0.8, phrase_time_limit=3.0)
                        if audio:
                            text_heard = ""
                            check_langs = list(
                                dict.fromkeys(
                                    [
                                        SUPPORTED_LANGUAGES.get(_last_detected_language, {}).get("stt_code", "en-IN"),
                                        "en-IN",
                                        "hi-IN",
                                    ]
                                )
                            )
                            for l_code in check_langs:
                                try:
                                    text_heard = recognizer.recognize_google(audio, language=l_code).lower().strip()
                                    if text_heard:
                                        break
                                except Exception:
                                    continue

                            if text_heard:
                                is_stop = any(cmd in text_heard for cmd in STOP_COMMANDS)
                                if is_stop:
                                    stop_speaking()
                                    break
                    except sr.WaitTimeoutError:
                        continue
                    except Exception:
                        break
        except Exception as e:
            logging.debug(f"Barge-in monitor notice: {e}")
        finally:
            _mic_lock.release()

    barge_in_thread = threading.Thread(target=_barge_in_listener, daemon=True)
    barge_in_thread.start()

    while _mixer_ready and pygame.mixer.music.get_busy():
        if _speech_stop:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            break
        await asyncio.sleep(0.05)

    _is_speaking = False

    try:
        pygame.mixer.music.unload()
    except Exception:
        pass

    _safe_remove(temp_voice_file)

def say(text: str) -> None:
    global _speech_stop
    _speech_stop = False
    print(text)

    with _tts_lock:
        try:
            _async_worker.run_coroutine(_edge_tts_speak(str(text)))
        except Exception as e:
            logging.error(f"TTS Execution failure: {e}")

def speak(text: str) -> None:
    say(text)

# ---------------------------------------------------------------------------
# Listening & Microphone Calibration with Multilingual Detection
# ---------------------------------------------------------------------------

def _calibrate_microphone(source: sr.AudioSource) -> None:
    global _mic_calibrated
    if not _mic_calibrated:
        recognizer.adjust_for_ambient_noise(source, duration=0.8)
        _mic_calibrated = True

def _normalize_whisper_language(language: str | None) -> str | None:
    """Map Whisper's ISO language code to internal language key."""
    if not language:
        return None

    value = str(language).strip().lower()
    aliases = {
        "en": "en", "english": "en",
        "hi": "hi", "hindi": "hi",
        "es": "es", "spanish": "es",
        "fr": "fr", "french": "fr",
        "de": "de", "german": "de",
        "it": "it", "italian": "it",
        "pt": "pt", "portuguese": "pt",
        "ru": "ru", "russian": "ru",
        "ar": "ar", "arabic": "ar",
        "zh": "zh", "chinese": "zh",
        "ja": "ja", "japanese": "ja",
        "ko": "ko", "korean": "ko",
        "bn": "bn", "bengali": "bn",
        "pa": "pa", "punjabi": "pa",
        "gu": "gu", "gujarati": "gu",
        "mr": "mr", "marathi": "mr",
        "ta": "ta", "tamil": "ta",
        "te": "te", "telugu": "te",
        "kn": "kn", "kannada": "kn",
        "ml": "ml", "malayalam": "ml",
        "ur": "ur", "urdu": "ur",
        "tr": "tr", "turkish": "tr",
        "nl": "nl", "dutch": "nl",
        "pl": "pl", "polish": "pl",
        "id": "id", "indonesian": "id",
    }
    return aliases.get(value)

def _infer_romanized_language(text: str) -> str | None:
    """Best-effort language inference for Latin-script speech such as Roman Gujarati."""
    normalized = re.sub(r"[^a-z0-9' ]+", " ", text.lower())
    words = set(normalized.split())

    # Strong phrase/word signals for Roman Gujarati. These are deliberately
    # conservative so ordinary English is not accidentally relabeled Gujarati.
    gujarati_phrases = (
        "taru naam", "tamaru naam", "maru naam", "shu che", "shu chhe",
        "su che", "su chhe", "kem cho", "kem chho", "tame kem",
        "hu chu", "hu chhu", "mane", "tame", "tamare", "tamaru",
        "maru", "mari", "che", "chhe", "chho", "shu", "su",
        "kem", "kyare", "kya", "nathi", "nahi", "karo", "karvu",
        "joiye", "aapo", "aapjo", "have", "aaje", "kaam", "sachu",
        "maru naam shu che", "tamaru naam shu che", "taru naam shu che",
        "kem cho tame", "hu majama chu", "hu maja ma chu",
    )
    gu_score = sum(2 if phrase in normalized else 1 for phrase in gujarati_phrases)

    # Roman Hindi/Hinglish signals, kept separate so Gujarati remains preferred
    # when Gujarati-specific phrases are present.
    hindi_phrases = (
        "tumhara naam", "mera naam", "kya hai", "kaise ho", "kaisa ho",
        "mujhe", "tumhe", "aapko", "karo", "karna", "chahiye", "kyun",
        "kahan", "kab", "hai", "ho", "haan", "nahi", "mera", "meri",
        "tumhara", "aapka",
    )
    hi_score = sum(2 if phrase in normalized else 1 for phrase in hindi_phrases)

    # Only override Whisper's Latin-script English classification when there
    # is meaningful evidence. This fixes Roman Gujarati such as "taru naam shu che".
    # Strong Gujarati signals must win even when Whisper/Google labels
    # Latin-script Gujarati as English.
    if gu_score >= 2 and gu_score > hi_score:
        return "gu"
    if hi_score >= 4 and hi_score > gu_score:
        return "hi"
    return None

def _transcribe_with_groq(audio: sr.AudioData) -> tuple[str, str | None]:
    """Transcribe speech with multilingual Whisper and preserve the spoken language."""
    if groq_client is None:
        return "", None

    wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)
    transcription = groq_client.audio.transcriptions.create(
        file=("jarvis_input.wav", wav_bytes),
        model=GROQ_STT_MODEL,
        response_format="verbose_json",
        temperature=0.0,
    )

    text = str(getattr(transcription, "text", "") or "").strip().lower()
    detected = _normalize_whisper_language(getattr(transcription, "language", None))

    if not text and isinstance(transcription, dict):
        text = str(transcription.get("text", "") or "").strip().lower()
        detected = _normalize_whisper_language(transcription.get("language"))

    if text:
        script_lang = _detect_text_script_lang(text)

        # Non-Latin scripts are stronger evidence than a generic Whisper label.
        for ch in text:
            if ord(ch) > 0x024F:
                if script_lang in SUPPORTED_LANGUAGES:
                    detected = script_lang
                break

        # Whisper can label Romanized Gujarati as English because the text uses
        # Latin characters. Prefer a conservative Gujarati/Hindi heuristic.
        romanized_lang = _infer_romanized_language(text)
        if romanized_lang in SUPPORTED_LANGUAGES:
            detected = romanized_lang

    if detected is None and text:
        detected = _detect_text_script_lang(text)

    return text, detected


def listen(timeout: float | None = None, phrase_time_limit: float = 5) -> str:
    """Capture one utterance reliably while keeping multilingual detection intact."""
    global _last_detected_language

    with _mic_lock:
        try:
            with get_working_microphone() as source:
                _calibrate_microphone(source)
                audio = recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )
        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as exc:
            logging.error(f"Speech recognition service error: {exc}")
            return ""
        except Exception as exc:
            logging.error(f"Listen/microphone error: {exc}")
            return ""

        # PRIMARY PATH: Groq Whisper multilingual STT.
        if groq_client is not None:
            try:
                text, detected_lang = _transcribe_with_groq(audio)
                if text:
                    if detected_lang in SUPPORTED_LANGUAGES:
                        _last_detected_language = detected_lang
                    else:
                        script_lang = _detect_text_script_lang(text)
                        romanized_lang = _infer_romanized_language(text)
                        if romanized_lang in SUPPORTED_LANGUAGES:
                            _last_detected_language = romanized_lang
                        elif script_lang in SUPPORTED_LANGUAGES:
                            _last_detected_language = script_lang
                        elif not _last_detected_language:
                            _last_detected_language = _current_language or "en"

                    lang_name = SUPPORTED_LANGUAGES.get(
                        _last_detected_language, SUPPORTED_LANGUAGES["en"]
                    )["name"]
                    print(f"You ({lang_name}):", text)
                    return text
            except Exception as exc:
                logging.debug(
                    f"Groq Whisper STT notice ({exc}), using Google fallback..."
                )

        # FALLBACK PATH: try the most likely languages first.
        candidate_langs = []
        priority = [_last_detected_language, _current_language]
        for lang_code in priority:
            if lang_code in SUPPORTED_LANGUAGES and lang_code not in candidate_langs:
                candidate_langs.append(lang_code)

        # Keep the existing full-language fallback so no supported language is lost.
        for lang_code in SUPPORTED_LANGUAGES:
            if lang_code not in candidate_langs:
                candidate_langs.append(lang_code)

        for lang_code in candidate_langs:
            stt_code = SUPPORTED_LANGUAGES[lang_code]["stt_code"]
            try:
                text = recognizer.recognize_google(
                    audio, language=stt_code
                ).lower().strip()
                if text:
                    romanized_lang = _infer_romanized_language(text)
                    _last_detected_language = (
                        romanized_lang if romanized_lang in SUPPORTED_LANGUAGES else lang_code
                    )
                    lang_name = SUPPORTED_LANGUAGES[_last_detected_language]["name"]
                    print(f"You ({lang_name}):", text)
                    return text
            except (sr.UnknownValueError, sr.RequestError):
                continue

        return ""


def is_wake_phrase(text: str) -> bool:
    text = text.strip().lower()
    if not text:
        return False
    if text in WAKE_SINGLE_WORDS:
        return True
    return any(phrase in text for phrase in WAKE_PHRASES)

# ---------------------------------------------------------------------------
# Local Persistent Data Managers (JSON Storage)
# ---------------------------------------------------------------------------

def _load_json(file_path: str, default_val: type) -> type:
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_val
    return default_val

def _save_json(file_path: str, data: type) -> None:
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save {file_path}: {e}")

# 1. Configuration & Preferences
user_config = _load_json(CONFIG_FILE, {"language": "en"})
_current_language = user_config.get("language", "en")

def set_preferred_language(lang_code_or_name: str) -> str:
    global _current_language
    target = lang_code_or_name.strip().lower()

    found_code = None
    for code, info in SUPPORTED_LANGUAGES.items():
        if target == code or target == info["name"].lower():
            found_code = code
            break

    if found_code:
        _current_language = found_code
        user_config["language"] = found_code
        _save_json(CONFIG_FILE, user_config)
        lang_name = SUPPORTED_LANGUAGES[found_code]["name"]
        return f"Language changed to {lang_name}."
    else:
        return f"Language {lang_code_or_name} is not currently supported."

# 2. Conversation History & Context
conversation_history = _load_json(HISTORY_FILE, [])

def save_history(user_msg: str, bot_msg: str) -> None:
    conversation_history.append({"user": user_msg, "bot": bot_msg})
    if len(conversation_history) > 20:
        conversation_history.pop(0)
    _save_json(HISTORY_FILE, conversation_history)

def clear_history() -> None:
    conversation_history.clear()
    _save_json(HISTORY_FILE, conversation_history)

# 3. User Explicit Memory
user_memories = _load_json(MEMORY_FILE, [])

def add_memory(fact: str) -> None:
    if fact not in user_memories:
        user_memories.append(fact)
        _save_json(MEMORY_FILE, user_memories)

def clear_memory() -> None:
    user_memories.clear()
    _save_json(MEMORY_FILE, user_memories)

# 4. Custom Voice Shortcuts
custom_shortcuts = _load_json(SHORTCUTS_FILE, {})

def save_shortcuts() -> None:
    _save_json(SHORTCUTS_FILE, custom_shortcuts)

# 5. Reminders Storage
reminders_list = _load_json(REMINDERS_FILE, [])

def save_reminders() -> None:
    _save_json(REMINDERS_FILE, reminders_list)

# ---------------------------------------------------------------------------
# Background Task Runners (Reminders & Battery Monitor)
# ---------------------------------------------------------------------------

_battery_alert_triggered = False

def _background_monitor_loop() -> None:
    global _battery_alert_triggered
    while True:
        try:
            # 1. Reminders Check
            now = datetime.now()
            to_remove = []
            for rem in list(reminders_list):
                try:
                    rem_time = datetime.fromisoformat(rem["time"])
                    if now >= rem_time:
                        say(f"Reminder alert: {rem['text']}")
                        to_remove.append(rem)
                except Exception:
                    to_remove.append(rem)

            if to_remove:
                for r in to_remove:
                    if r in reminders_list:
                        reminders_list.remove(r)
                save_reminders()

            # 2. Low Battery Check
            if HAS_PSUTIL:
                battery = psutil.sensors_battery()
                if battery:
                    percent = battery.percent
                    is_plugged = battery.power_plugged
                    if percent <= 20 and not is_plugged:
                        if not _battery_alert_triggered:
                            say(
                                f"Warning Sir, your battery is low at {percent} percent. Please plug in your charger."
                            )
                            _battery_alert_triggered = True
                    elif percent > 25 or is_plugged:
                        _battery_alert_triggered = False
        except Exception as e:
            logging.error(f"Background loop error: {e}")

        time.sleep(10)

threading.Thread(target=_background_monitor_loop, daemon=True).start()

# ---------------------------------------------------------------------------
# AI Query Core (Ollama with Groq Failover + Multilingual Support)
# ---------------------------------------------------------------------------

def _build_context_prompt(prompt: str) -> str:
    lang_name = SUPPORTED_LANGUAGES.get(_last_detected_language, {}).get(
        "name", "English"
    )
    context = (
        f"You are Jarvis. The user input was detected in {lang_name}. "
        f"Respond ONLY IN {lang_name}. Output exactly ONE response. "
        f"Do NOT translate, duplicate, or repeat the response in any other language. "
        f"Keep the answer concise and suitable for text-to-speech.\n"
    )
    if user_memories:
        context += "Known facts about user:\n" + "\n".join(
            f"- {m}" for m in user_memories
        ) + "\n\n"
    if conversation_history:
        context += "Recent history:\n"
        for ex in conversation_history[-3:]:
            context += f"User: {ex['user']}\nJarvis: {ex['bot']}\n"
        context += "\n"
    context += f"User: {prompt}"
    return context

def ask_ollama(prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": _build_context_prompt(prompt),
        "stream": False,
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()["response"].strip()

def ask_groq(prompt: str) -> str:
    if groq_client is None:
        raise RuntimeError("Groq API key not configured")

    lang_name = SUPPORTED_LANGUAGES.get(_last_detected_language, {}).get(
        "name", "English"
    )
    messages = [
        {
            "role": "system",
            "content": (
                f"You are Jarvis, a helpful voice assistant. Keep answers concise, direct, "
                f"and suitable for text-to-speech. Respond ONLY in {lang_name}. Produce exactly ONE answer. "
                f"Never provide a second translation, summary, or duplicate in another language."
            ),
        }
    ]
    if user_memories:
        messages.append(
            {
                "role": "system",
                "content": "User Facts:\n" + "\n".join(user_memories),
            }
        )
    for ex in conversation_history[-3:]:
        messages.append({"role": "user", "content": ex["user"]})
        messages.append({"role": "assistant", "content": ex["bot"]})

    messages.append({"role": "user", "content": prompt})

    completion = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        max_tokens=256,
    )
    return completion.choices[0].message.content.strip()

def ask_ai(prompt: str) -> str:
    try:
        reply = ask_ollama(prompt)
    except Exception as ollama_error:
        logging.debug(f"Ollama error ({ollama_error}), failing over to Groq...")
        reply = ask_groq(prompt)

    # Keep normal spoken answers to one clean line without deleting content.
    reply = " ".join(str(reply).split())
    save_history(prompt, reply)
    return reply

# ---------------------------------------------------------------------------
# Feature Implementation Utilities
# ---------------------------------------------------------------------------

def _play_local_music() -> None:
    if not os.path.isdir(MUSIC_FOLDER):
        say("No music folder found on this computer.")
        return

    songs = [
        f
        for f in os.listdir(MUSIC_FOLDER)
        if f.lower().endswith((".mp3", ".wav", ".flac", ".m4a", ".ogg"))
    ]
    if not songs:
        say("No music files found.")
        return

    os.startfile(os.path.join(MUSIC_FOLDER, random.choice(songs)))
    say("Playing music from your library.")

def _play_youtube(song: str) -> None:
    say(f"Playing {song} on YouTube")
    if HAS_PYWHATKIT:
        try:
            pywhatkit.playonyt(song)
            return
        except Exception as exc:
            logging.debug(f"pywhatkit error ({exc}), switching to browser fallback...")

    query = urllib.parse.quote_plus(song)
    webbrowser.open(f"https://www.youtube.com/results?search_query={query}")

def _get_weather(city: str) -> str:
    if not OPENWEATHER_API_KEY:
        return "Weather service is unconfigured. Please set your OpenWeather API key environment variable."
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={urllib.parse.quote_plus(city)}&appid={OPENWEATHER_API_KEY}&units=metric"
        res = requests.get(url, timeout=10).json()
        if res.get("cod") != 200:
            return f"Could not find weather details for {city}."
        desc = res["weather"][0]["description"]
        temp = round(res["main"]["temp"])
        feels_like = round(res["main"]["feels_like"])
        return f"In {city}, it is currently {temp} degrees Celsius with {desc}, feeling like {feels_like} degrees."
    except Exception as e:
        logging.error(f"Weather API error: {e}")
        return "Unable to retrieve weather information right now."

def _search_files(query: str, extension: str | None = None) -> list[str]:
    search_dirs = [
        os.path.join(os.path.expanduser("~"), folder)
        for folder in ("Desktop", "Documents", "Downloads", "Music")
    ]
    found_files = []
    query_lower = query.lower().strip()

    for directory in search_dirs:
        if not os.path.exists(directory):
            continue
        for root, dirs, files in os.walk(directory):
            # Include directories as well as files so folder commands work.
            for dirname in dirs:
                if query_lower in dirname.lower() and extension is None:
                    found_files.append(os.path.join(root, dirname))
                    if len(found_files) >= 5:
                        return found_files

            for file in files:
                f_lower = file.lower()
                if query_lower in f_lower:
                    if extension is None or f_lower.endswith(extension.lower()):
                        found_files.append(os.path.join(root, file))
                        if len(found_files) >= 5:
                            return found_files
    return found_files

def _parse_and_add_reminder(command: str) -> str:
    in_match = re.search(
        r"remind me in (\d+)\s*(minute|minutes|hour|hours|second|seconds) to (.+)",
        command,
        re.IGNORECASE,
    )
    if in_match:
        val = int(in_match.group(1))
        unit = in_match.group(2).lower()
        text = in_match.group(3).strip()

        if "second" in unit:
            delta = timedelta(seconds=val)
        elif "hour" in unit:
            delta = timedelta(hours=val)
        else:
            delta = timedelta(minutes=val)

        rem_time = datetime.now() + delta
        reminders_list.append({"text": text, "time": rem_time.isoformat()})
        save_reminders()
        return f"Reminder set for {text} in {val} {unit}."

    at_match = re.search(
        r"remind me at (\d{1,2})(?::(\d{2}))?\s*(am|pm)? to (.+)",
        command,
        re.IGNORECASE,
    )
    if at_match:
        hr = int(at_match.group(1))
        mn = int(at_match.group(2)) if at_match.group(2) else 0
        ampm = at_match.group(3).lower() if at_match.group(3) else None
        text = at_match.group(4).strip()

        if ampm:
            if ampm == "pm" and hr < 12:
                hr += 12
            elif ampm == "am" and hr == 12:
                hr = 0

        now = datetime.now()
        try:
            rem_time = now.replace(hour=hr, minute=mn, second=0, microsecond=0)
        except ValueError:
            return "Invalid time provided for the reminder."

        if rem_time <= now:
            rem_time += timedelta(days=1)

        reminders_list.append({"text": text, "time": rem_time.isoformat()})
        save_reminders()
        return f"Reminder set for {text} at {rem_time.strftime('%I:%M %p')}."

    return "Please specify a clear time and task, for example: remind me in 10 minutes to drink water."

# ---------------------------------------------------------------------------
# Command Processor Logic
# ---------------------------------------------------------------------------

def execute_command(command: str) -> None:
    print("Command received:", command)
    cmd = command.lower().strip()

    if not cmd:
        return

    # Check for User Custom Voice Shortcuts first
    for sc_name, sc_action in list(custom_shortcuts.items()):
        if sc_name in cmd:
            say(f"Executing shortcut {sc_name}")
            execute_command(sc_action)
            return

    # --- 0. Multilingual Configuration Commands ---
    if "what language are you using" in cmd or "which language" in cmd:
        lang_name = SUPPORTED_LANGUAGES.get(
            _last_detected_language, SUPPORTED_LANGUAGES["en"]
        )["name"]
        say(f"Current detected language is {lang_name}.")
        return

    if "change language to" in cmd or "set language to" in cmd or "bhasha badlo" in cmd:
        target_lang = (
            cmd.replace("change language to", "")
            .replace("set language to", "")
            .replace("bhasha badlo", "")
            .strip()
        )
        say(set_preferred_language(target_lang))

    elif "list languages" in cmd or "supported languages" in cmd:
        lang_names = ", ".join([v["name"] for v in SUPPORTED_LANGUAGES.values()])
        say(f"I support the following languages: {lang_names}")

    # --- 1. Memory & History Commands ---
    elif "remember that" in cmd:
        fact = cmd.split("remember that", 1)[1].strip()
        if fact:
            add_memory(fact)
            say(f"I will remember that {fact}")
        else:
            say("What would you like me to remember?")

    elif "what do you remember" in cmd or "recall memory" in cmd:
        if user_memories:
            say("Here is what I remember about you: " + ". ".join(user_memories))
        else:
            say("I do not have any saved memories yet.")

    elif "forget my memory" in cmd or "clear memory" in cmd:
        clear_memory()
        say("I have cleared all your stored personal memories.")

    elif "clear conversation history" in cmd or "clear history" in cmd:
        clear_history()
        say("Conversation history cleared.")

    # --- 2. System Monitoring Commands ---
    elif "cpu usage" in cmd or "cpu performance" in cmd:
        if HAS_PSUTIL:
            say(f"Current CPU usage is {psutil.cpu_percent(interval=1)} percent.")
        else:
            say("psutil library is not installed.")

    elif "ram usage" in cmd or "memory usage" in cmd:
        if HAS_PSUTIL:
            ram = psutil.virtual_memory()
            say(
                f"RAM usage is currently at {ram.percent} percent. {round(ram.used / (1024 ** 3), 1)} gigabytes of {round(ram.total / (1024 ** 3), 1)} gigabytes used."
            )
        else:
            say("psutil library is not installed.")

    elif "battery" in cmd:
        if HAS_PSUTIL:
            batt = psutil.sensors_battery()
            if batt:
                status = "plugged in" if batt.power_plugged else "unplugged"
                say(
                    f"Your battery level is at {batt.percent} percent and status is {status}."
                )
            else:
                say("Battery status is unavailable on this hardware.")
        else:
            say("psutil library is not installed.")

    # --- 3. Weather Commands ---
    elif "weather" in cmd or "mausam" in cmd:
        city = DEFAULT_CITY
        if "in " in cmd:
            city = cmd.split("in ", 1)[1].strip()
        elif "me " in cmd:
            city = cmd.split("me ", 1)[1].strip()
        say(_get_weather(city))

    # --- 4. News Search Commands ---
    elif "news" in cmd or "khabar" in cmd:
        topic = "latest"
        if "about " in cmd:
            topic = cmd.split("about ", 1)[1].strip()
        say(f"Searching for news regarding {topic}")
        webbrowser.open(
            f"https://news.google.com/search?q={urllib.parse.quote_plus(topic)}"
        )

    # --- 5. Clipboard Control Commands ---
    elif "read clipboard" in cmd or "what is in my clipboard" in cmd:
        if HAS_PYPERCLIP:
            text = pyperclip.paste().strip()
            if text:
                say(f"Clipboard contents: {text}")
            else:
                say("Your clipboard is currently empty.")
        else:
            say("pyperclip library is not installed.")

    elif "copy to clipboard" in cmd or "copy text" in cmd:
        if HAS_PYPERCLIP:
            text = (
                cmd.replace("copy to clipboard", "")
                .replace("copy text", "")
                .strip()
            )
            if text:
                pyperclip.copy(text)
                say(f"Copied {text} to clipboard.")
            else:
                say("What text should I copy to the clipboard?")
        else:
            say("pyperclip library is not installed.")

    elif "clear clipboard" in cmd:
        if HAS_PYPERCLIP:
            pyperclip.copy("")
            say("Clipboard cleared.")
        else:
            say("pyperclip library is not installed.")

    # --- 6. Local File Search ---
    elif "find file" in cmd or "search file" in cmd or "find pdf" in cmd:
        ext = ".pdf" if "pdf" in cmd else None
        target = (
            cmd.replace("find file named", "")
            .replace("find file", "")
            .replace("search file", "")
            .replace("find pdf files", "")
            .replace("find pdf", "")
            .strip()
        )
        if target:
            say(f"Searching for {target}")
            results = _search_files(target, ext)
            if results:
                say(
                    f"Found {len(results)} matching files. Opening the location of the first match."
                )
                os.system(f'explorer /select,"{results[0]}"')
            else:
                say("No matching files found in user folders.")
        else:
            say("What file name should I search for?")

    # --- 7. File and Folder Management ---
    elif cmd.startswith("create folder"):
        foldername = cmd.replace("create folder", "").strip()
        if foldername:
            target_path = os.path.join(
                os.path.expanduser("~"), "Desktop", foldername
            )
            try:
                os.makedirs(target_path, exist_ok=True)
                say(f"Folder {foldername} created on Desktop.")
            except Exception as e:
                say(f"Failed to create folder: {e}")
        else:
            say("Please specify a folder name.")

    elif cmd.startswith("create file") or cmd.startswith("create text file"):
        filename = (
            cmd.replace("create text file", "")
            .replace("create file", "")
            .strip()
        )
        if filename:
            if not filename.endswith(".txt"):
                filename += ".txt"
            target_path = os.path.join(
                os.path.expanduser("~"), "Desktop", filename
            )
            try:
                with open(target_path, "w") as f:
                    f.write("")
                say(f"Text file {filename} created on Desktop.")
            except Exception as e:
                say(f"Failed to create file: {e}")
        else:
            say("Please specify a file name.")

    elif "delete file" in cmd or "delete folder" in cmd:
        item = (
            cmd.replace("delete file", "").replace("delete folder", "").strip()
        )
        if item:
            matches = _search_files(item)
            if matches:
                target = matches[0]
                say(
                    f"Are you sure you want to permanently delete {os.path.basename(target)}? Reply yes or no."
                )
                confirm = listen(timeout=30, phrase_time_limit=8)
                if "yes" in confirm or "sure" in confirm or "haan" in confirm:
                    try:
                        if os.path.isdir(target):
                            shutil.rmtree(target)
                        else:
                            os.remove(target)
                        say("Item deleted successfully.")
                    except Exception as e:
                        say(f"Failed to delete item: {e}")
                else:
                    say("Deletion cancelled.")
            else:
                say("Could not find the specified file or folder to delete.")
        else:
            say("Please specify which item to delete.")

    elif "open file" in cmd or "open folder" in cmd:
        item = cmd.replace("open file", "").replace("open folder", "").strip()
        if item:
            matches = _search_files(item)
            if matches:
                say(f"Opening {os.path.basename(matches[0])}")
                os.startfile(matches[0])
            else:
                say("Could not locate the requested file or folder.")
        else:
            say("What file or folder should I open?")

    # --- 8. Reminders Commands ---
    elif cmd.startswith("remind me"):
        say(_parse_and_add_reminder(cmd))

    elif "show reminders" in cmd or "list reminders" in cmd:
        if reminders_list:
            response = "You have the following active reminders: "
            for idx, r in enumerate(reminders_list, 1):
                try:
                    t_str = datetime.fromisoformat(r["time"]).strftime(
                        "%I:%M %p on %d %b"
                    )
                    response += f"{idx}. {r['text']} at {t_str}. "
                except Exception:
                    response += f"{idx}. {r['text']}. "
            say(response)
        else:
            say("You have no active reminders.")

    elif "cancel reminder" in cmd or "clear reminders" in cmd or "cancel my reminder" in cmd:
        reminders_list.clear()
        save_reminders()
        say("All active reminders have been cancelled and cleared.")

    # --- 9. Custom Voice Shortcuts Creation ---
    elif cmd.startswith("create shortcut"):
        parts = cmd.replace("create shortcut", "").split("to", 1)
        if len(parts) == 2:
            sc_name = parts[0].strip()
            sc_action = parts[1].strip()
            if sc_name and sc_action:
                custom_shortcuts[sc_name] = sc_action
                save_shortcuts()
                say(f"Created voice shortcut {sc_name} to execute {sc_action}")
            else:
                say("Shortcut definition incomplete.")
        else:
            say(
                "Please state the shortcut format, for example: create shortcut study mode to open chrome"
            )

    # --- 10. Core Jarvis Commands ---
    elif (
        "hello" in cmd
        or "namaste" in cmd
        or "hola" in cmd
        or "bonjour" in cmd
        or "kem cho" in cmd
        or "kem chho" in cmd
        or "નમસ્તે" in cmd
        or "હેલો" in cmd
    ):
        if _last_detected_language == "gu":
            say("નમસ્તે સર.")
        elif _last_detected_language == "hi":
            say("नमस्ते सर.")
        else:
            say("Hello Sir.")
    elif (
        "how are you" in cmd
        or "kaise ho" in cmd
        or "kem cho" in cmd
        or "kem chho" in cmd
        or "કેમ છો" in cmd
    ):
        if _last_detected_language == "gu":
            say("હું મજામાં છું સર. પૂછવા બદલ આભાર.")
        elif _last_detected_language == "hi":
            say("मैं ठीक हूँ सर। पूछने के लिए धन्यवाद।")
        else:
            say("I am fine Sir. Thank you for asking.")
    elif (
        "your name" in cmd
        or "tumhara naam" in cmd
        or "taru naam" in cmd
        or "tamaru naam" in cmd
        or "તમારું નામ" in cmd
        or "તારું નામ" in cmd
    ):
        if _last_detected_language == "gu":
            say("મારું નામ Jarvis છે.")
        elif _last_detected_language == "hi":
            say("मेरा नाम Jarvis है।")
        else:
            say("My name is Jarvis.")
    elif "time" in cmd or "samay" in cmd or "waqt" in cmd:
        say("The time is " + datetime.now().strftime("%I:%M %p"))
    elif "date" in cmd or "tarikh" in cmd:
        say(f"Today's date is {datetime.now().strftime('%d %B %Y')}")
    elif "volume up" in cmd or "आवाज बढ़ाओ" in cmd:
        keyboard.press_and_release("volume up")
        say("Volume increased")
    elif "volume down" in cmd or "आवाज कम करो" in cmd:
        keyboard.press_and_release("volume down")
        say("Volume decreased")
    elif "mute" in cmd:
        keyboard.press_and_release("volume mute")
        say("Volume muted")
    elif "google" in cmd and "search" not in cmd:
        say("Opening Google")
        webbrowser.open("https://www.google.com")
    elif "youtube" in cmd and not cmd.startswith("play"):
        say("Opening YouTube")
        webbrowser.open("https://www.youtube.com")
    elif "calculator" in cmd:
        os.system("start calc")
    elif "notepad" in cmd:
        os.system("start notepad")
    elif "paint" in cmd:
        os.system("start mspaint")
    elif "file explorer" in cmd or "explorer" in cmd:
        os.system("start explorer")
    elif "settings" in cmd:
        os.system("start ms-settings:")
    elif (
            "play music" in cmd
            or "play song" in cmd
            or cmd.startswith("play ")
            or cmd.startswith("song ")
            or cmd.startswith("gana ")
    ):
        song = cmd
        for word in ("play music", "play song", "play", "song", "gana", "music"):
            song = song.replace(word, "")
        song = song.strip()

        if song:
            _play_youtube(song)
        elif "play music" in cmd or cmd in ("play", "play song", "gana"):
            _play_local_music()
        else:
            say("Which song should I play?")
    elif "search" in cmd:
        query = cmd.replace("search", "").strip()
        if query:
            say(f"Searching Google for {query}")
            webbrowser.open(
                "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
            )
        else:
            say("What should I search?")
    elif "camera" in cmd:
        say("Opening Camera")
        os.system("start microsoft.windows.camera:")
    elif "downloads" in cmd:
        os.startfile(os.path.join(os.path.expanduser("~"), "Downloads"))
    elif "documents" in cmd:
        os.startfile(os.path.join(os.path.expanduser("~"), "Documents"))
    elif "desktop" in cmd:
        os.startfile(os.path.join(os.path.expanduser("~"), "Desktop"))
    elif "chrome" in cmd:
        say("Opening Chrome")
        os.system("start chrome")
    elif "cmd" in cmd or "command prompt" in cmd:
        say("Opening Command Prompt")
        os.system("start cmd")
    elif "shutdown" in cmd:
        say("Shutting down the computer")
        os.system("shutdown /s /t 5")
    elif "restart" in cmd:
        say("Restarting the computer")
        os.system("shutdown /r /t 5")
    elif "lock" in cmd:
        say("Locking the computer")
        os.system("rundll32.exe user32.dll,LockWorkStation")
    elif "exit application" in cmd or "shutdown jarvis" in cmd or "quit jarvis" in cmd:
        say("Goodbye Sir. Have a nice day.")
        sys.exit(0)
    elif any(stop_word == cmd for stop_word in ("stop", "exit", "goodbye", "alvida")):
        say("Stopping session.")
        return
    else:
        try:
            say(ask_ai(cmd))
        except Exception as exc:
            logging.error(f"AI response error: {exc}")
            say("Sorry Sir, I could not process your request.")

# ---------------------------------------------------------------------------
# Main Session Loops & Entry Point
# ---------------------------------------------------------------------------

class _OpenWakeWordListener:
    """Adapter for official openWakeWord API with safety mechanisms."""

    def __init__(self):
        if not HAS_OPENWAKEWORD:
            raise RuntimeError("openWakeWord dependencies are not installed.")

        try:
            openwakeword.utils.download_models()
        except Exception as exc:
            logging.debug(f"openWakeWord model download notice: {exc}")

        model_path = None
        try:
            paths = openwakeword.get_pretrained_model_paths()
            for candidate in paths:
                name = os.path.basename(str(candidate)).lower()
                if "hey_jarvis" in name or "hey-jarvis" in name:
                    model_path = candidate
                    break
        except Exception:
            pass

        if model_path:
            self.model = OpenWakeWordModel(wakeword_models=[model_path])
        else:
            self.model = OpenWakeWordModel()

        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1280,
        )
        self.threshold = 0.35
        self._cleared = False
        self._stopped = False

    def wait(self) -> bool:
        while not self._stopped:
            try:
                data = self.stream.read(1280, exception_on_overflow=False)
                frame = np.frombuffer(data, dtype=np.int16)
                predictions = self.model.predict(frame)

                for name, score in predictions.items():
                    if "hey_jarvis" in str(name).lower() and float(score) >= self.threshold:
                        self._cleared = False
                        return True
            except Exception as e:
                logging.error(f"Wake word stream error: {e}")
                time.sleep(0.1)
        return False

    def pause(self) -> None:
        """Release the wake-word audio stream while speech recognition is active."""
        try:
            if getattr(self, "stream", None) is not None and self.stream.is_active():
                self.stream.stop_stream()
        except Exception as exc:
            logging.debug(f"Wake-word pause notice: {exc}")

    def resume(self) -> None:
        """Re-open the wake-word stream after command listening is complete."""
        try:
            if getattr(self, "stream", None) is not None and not self.stream.is_active():
                self.stream.start_stream()
        except Exception as exc:
            logging.debug(f"Wake-word resume notice: {exc}")

    def clear(self) -> None:
        self._cleared = True
        try:
            if hasattr(self.model, "reset"):
                self.model.reset()
        except Exception:
            pass

    def stop(self) -> None:
        self._stopped = True
        try:
            self.stream.stop_stream()
            self.stream.close()
        except Exception:
            pass
        try:
            self.audio.terminate()
        except Exception:
            pass

def _command_session() -> None:
    """Listen for commands continuously until silence or sleep phrase."""
    say("Yes Sir")
    while True:
        command = listen(timeout=20, phrase_time_limit=8)
        if not command:
            if _speech_stop:
                command = listen(timeout=20, phrase_time_limit=8)
            if not command:
                say("Going back to sleep.")
                break
        if command in ("sleep", "go to sleep", "so jao"):
            say("Going to sleep.")
            break
        execute_command(command)

def _wait_for_wake_word_speech() -> bool:
    wake = listen(timeout=20, phrase_time_limit=8)
    return bool(wake and is_wake_phrase(wake))

def main() -> None:
    wake_listener = None

    if HAS_OPENWAKEWORD:
        try:
            wake_listener = _OpenWakeWordListener()
            print('Using official openWakeWord "hey_jarvis" detection.')
        except Exception as exc:
            logging.debug(f"openWakeWord unavailable ({exc}), using speech fallback.")
            wake_listener = None

    say("Jarvis is ready. Say Hey Jarvis to wake me.")

    try:
        if wake_listener:
            while True:
                if wake_listener.wait():
                    wake_listener.clear()
                    # openWakeWord and SpeechRecognition must not hold the
                    # microphone at the same time. Temporarily release the
                    # wake-word stream so command listening can hear the user.
                    wake_listener.pause()
                    try:
                        _command_session()
                    finally:
                        wake_listener.resume()
        else:
            while True:
                if _wait_for_wake_word_speech():
                    _command_session()
    except KeyboardInterrupt:
        print("\nShutting down Jarvis...")
    finally:
        if wake_listener:
            wake_listener.stop()

if __name__ == "__main__":
    main()