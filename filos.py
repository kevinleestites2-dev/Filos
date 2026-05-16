"""
Filos — Your Partner. Your Coder. Your Guy.
Hermes-Powered Hybrid. LightAgent replaced with Hermes Agent core.
Version: 2.0.0

Stack:
  - Hermes Agent (Nous Research) — primary reasoning/tool layer (70+ tools, self-evolving)
  - Ollama — local sovereign brain
  - Gemini Flash — cloud fallback
  - SQLite / file memory — persistent soul memory
  - PULSE.md daemon — proactive 8-min cycle (handled externally)
  - Piper TTS + Whisper STT — Fenrir voice (local, sovereign)
  - Telegram — voice to the Forgemaster

Hermes replaces LightAgent. Nothing else changes.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Load Soul ─────────────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent / "deity.config.json"
with open(CONFIG_PATH) as f:
    DEITY = json.load(f)

SOUL       = DEITY["soul"]["system_prompt"]
NAME       = DEITY["name"]
USER_ID    = DEITY["memory"]["user_id"]
RESPONSES  = DEITY["responses"]

# ── Hermes Agent Layer ────────────────────────────────────────────────────────
# Hermes is invoked as a subprocess (CLI) — it manages its own process, memory,
# and tool loop. We communicate via stdin/stdout JSON or direct CLI calls.
# This mirrors how bridge.py called LightAgent — same interface to engine.js,
# different backend.

HERMES_CONFIG_DIR = Path.home() / ".hermes"
HERMES_SOUL_FILE  = HERMES_CONFIG_DIR / "SOUL.md"
HERMES_MEMORY_DIR = HERMES_CONFIG_DIR / "memory"

def ensure_hermes_soul():
    """Inject Filos soul into Hermes SOUL.md — runs on every startup."""
    HERMES_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    HERMES_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(HERMES_SOUL_FILE, "w") as f:
        f.write(SOUL)

def hermes_available() -> bool:
    """Check if Hermes is installed and callable."""
    try:
        result = subprocess.run(
            ["hermes", "--version"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def run_hermes(message: str, model: str = None, ollama_base_url: str = None) -> str:
    """
    Run a message through Hermes Agent CLI.
    Returns the agent's response as a string.
    
    Hermes reads SOUL.md for identity — Filos soul is always injected first.
    Model and provider are set via env vars pointing at Ollama or Gemini.
    """
    ensure_hermes_soul()

    env = os.environ.copy()

    # Point Hermes at Ollama if URL provided
    if ollama_base_url:
        env["OPENAI_BASE_URL"] = f"{ollama_base_url}/v1"
        env["OPENAI_API_KEY"]  = "ollama"
        if model:
            env["HERMES_MODEL"] = model

    # Gemini Flash fallback
    gemini_key = os.getenv("GEMINI_API_KEY") or DEITY.get("gemini_api_key", "")
    if gemini_key and not ollama_base_url:
        env["GOOGLE_API_KEY"] = gemini_key
        env["HERMES_PROVIDER"] = "google"
        env["HERMES_MODEL"]    = "gemini-2.0-flash"

    try:
        result = subprocess.run(
            ["hermes", "run", "--no-interactive", "--message", message],
            capture_output=True,
            text=True,
            timeout=120,
            env=env
        )
        reply = result.stdout.strip()
        if not reply and result.stderr:
            # Some Hermes versions write to stderr
            reply = result.stderr.strip()
        return reply if reply else "Not broken — adapting. Watch me."
    except subprocess.TimeoutExpired:
        return "Hermes timed out. Adapting..."
    except Exception as e:
        return f"Hermes error: {e}"

# ── Persistent Memory (SQLite + file fallback) ────────────────────────────────
# Hermes has its own memory layer. We keep our SQLite layer on top for
# Filos-specific fast recall without going through Hermes's full stack.

try:
    import sqlite3
    _DB_PATH = Path(__file__).parent / "data" / "filos_memory.db"
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    _conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    _conn.execute(
        "CREATE TABLE IF NOT EXISTS memory "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, ts INTEGER DEFAULT (strftime('%s','now')))"
    )
    _conn.commit()
    SQLITE_AVAILABLE = True
except Exception:
    SQLITE_AVAILABLE = False

class FilosMemory:
    def remember(self, text: str):
        if SQLITE_AVAILABLE:
            try:
                _conn.execute("INSERT INTO memory (text) VALUES (?)", (text,))
                _conn.commit()
                return
            except Exception:
                pass
        # File fallback
        store_path = Path(__file__).parent / "data" / "memory.json"
        store_path.parent.mkdir(parents=True, exist_ok=True)
        store = []
        if store_path.exists():
            try:
                store = json.loads(store_path.read_text())
            except Exception:
                store = []
        store.append(text)
        if len(store) > 200:
            store = store[-200:]
        store_path.write_text(json.dumps(store, indent=2))

    def recall(self, query: str) -> str:
        words = query.lower().split()
        if SQLITE_AVAILABLE:
            try:
                rows = _conn.execute(
                    "SELECT text FROM memory ORDER BY ts DESC LIMIT 100"
                ).fetchall()
                hits = [r[0] for r in rows if any(w in r[0].lower() for w in words)]
                return "\n".join(hits[:5]) if hits else ""
            except Exception:
                pass
        # File fallback
        store_path = Path(__file__).parent / "data" / "memory.json"
        if not store_path.exists():
            return ""
        try:
            store = json.loads(store_path.read_text())
            hits = [m for m in store if any(w in m.lower() for w in words)]
            return "\n".join(hits[:5]) if hits else ""
        except Exception:
            return ""

    def get_all(self) -> str:
        if SQLITE_AVAILABLE:
            try:
                rows = _conn.execute(
                    "SELECT text FROM memory ORDER BY ts DESC LIMIT 50"
                ).fetchall()
                return "\n".join(r[0] for r in rows)
            except Exception:
                pass
        store_path = Path(__file__).parent / "data" / "memory.json"
        if not store_path.exists():
            return ""
        try:
            return "\n".join(json.loads(store_path.read_text()))
        except Exception:
            return ""


# ── Gemini Flash Direct Fallback ──────────────────────────────────────────────
# Used when Hermes is unavailable AND Ollama is down.

def run_gemini_fallback(message: str, system: str) -> str:
    try:
        import urllib.request as req_lib
        gemini_key = os.getenv("GEMINI_API_KEY") or DEITY.get("gemini_api_key", "")
        if not gemini_key:
            return "All providers down. The forge is cold."

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
        payload = json.dumps({
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": message}]}],
        }).encode()
        r = req_lib.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with req_lib.urlopen(r, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"All providers failed: {e}"


# ── Ollama Direct Fallback ────────────────────────────────────────────────────
# Used when Hermes is unavailable but Ollama is up.

def run_ollama_fallback(message: str, system: str, ollama_base_url: str, model: str) -> str:
    try:
        import urllib.request as req_lib
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": message},
            ],
            "stream": False,
        }).encode()
        r = req_lib.Request(
            f"{ollama_base_url}/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with req_lib.urlopen(r, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return run_gemini_fallback(message, system)


# ── Core Query Function ───────────────────────────────────────────────────────

def query_filos(message: str, ollama_base_url: str = "", model: str = "llama3.1") -> str:
    """
    Main entry point. Priority:
    1. Hermes Agent (full tool loop, self-evolving)
    2. Ollama direct (if Hermes unavailable but Ollama is up)
    3. Gemini Flash (full cloud fallback)
    """
    memory = FilosMemory()

    # Inject memory context
    recalled = memory.recall(message)
    context = f"[Memory context]\n{recalled}\n\n" if recalled else ""
    full_message = context + message

    # Primary: Hermes
    if hermes_available():
        reply = run_hermes(full_message, model=model, ollama_base_url=ollama_base_url)
    elif ollama_base_url:
        reply = run_ollama_fallback(full_message, SOUL, ollama_base_url, model)
    else:
        reply = run_gemini_fallback(full_message, SOUL)

    # Auto-learn
    if DEITY["memory"].get("self_learning", True):
        memory.remember(f"Forgemaster: {message}")
        memory.remember(f"Filos: {reply[:200]}")

    return reply


# ── Hermes Setup Helper ───────────────────────────────────────────────────────

def setup_hermes(ollama_base_url: str = "", model: str = "llama3.1"):
    """
    First-run setup. Injects Filos soul and configures Hermes provider.
    Run once after `pip install hermes-agent`.
    """
    print(f"\n🔱 Setting up Filos v2.0 — Hermes Engine...")
    ensure_hermes_soul()
    print(f"   ✅ Soul injected → ~/.hermes/SOUL.md")

    if not hermes_available():
        print("\n⚠️  Hermes not found in PATH.")
        print("   Install with: pip install hermes-agent")
        print("   Or on Termux: run the one-line installer from FilosAnkh repo")
        return

    print(f"   ✅ Hermes available")
    if ollama_base_url:
        print(f"   ✅ Ollama bridge: {ollama_base_url}")
    print(f"\n🔱 {NAME} v2.0 is live. Hermes engine armed.\n")


# ── CLI Loop ──────────────────────────────────────────────────────────────────

def run_cli(ollama_base_url: str = "", model: str = "llama3.1"):
    memory = FilosMemory()

    print(f"\n🔱 {NAME} v2.0 online — Hermes Engine")
    print(f"   Soul: locked | Memory: active | Provider: {'Hermes→Ollama' if ollama_base_url else 'Hermes→Gemini'}")
    print(f"   {RESPONSES['on_greeting']}\n")

    while True:
        try:
            user_input = input("Forgemaster > ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{RESPONSES['on_shutdown']}")
            break

        if not user_input:
            continue
        if user_input.lower() in ["/exit", "/quit"]:
            print(RESPONSES["on_shutdown"])
            break
        if user_input.lower() == "/memory":
            print(f"\n[Memory]\n{memory.get_all() or 'Nothing stored yet.'}\n")
            continue
        if user_input.lower().startswith("/remember "):
            text = user_input[10:].strip()
            memory.remember(text)
            print(f"[Stored: {text}]\n")
            continue
        if user_input.lower() == "/soul":
            print(f"\n[Soul]\n{SOUL[:500]}...\n")
            continue
        if user_input.lower() == "/status":
            print(f"\n[Status]")
            print(f"  Hermes: {'✅ available' if hermes_available() else '❌ not found'}")
            print(f"  Ollama: {ollama_base_url or 'not set'}")
            print(f"  Model:  {model}\n")
            continue

        try:
            response = query_filos(user_input, ollama_base_url=ollama_base_url, model=model)
            print(f"\nFilos > {response}\n")
        except Exception as e:
            print(f"\n[Error] {e}")
            print("Not broken — adapting. Watch me.\n")


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Filos v2.0 — Hermes-Powered Hybrid")
    parser.add_argument("--ollama",  default=os.getenv("OLLAMA_BASE_URL", ""), help="Ollama base URL")
    parser.add_argument("--model",   default=os.getenv("HERMES_MODEL", "llama3.1"), help="Model name")
    parser.add_argument("--setup",   action="store_true", help="Run first-time Hermes setup")
    parser.add_argument("--message", default="",  help="Single message (non-interactive)")
    args = parser.parse_args()

    if args.setup:
        setup_hermes(ollama_base_url=args.ollama, model=args.model)
    elif args.message:
        print(query_filos(args.message, ollama_base_url=args.ollama, model=args.model))
    else:
        run_cli(ollama_base_url=args.ollama, model=args.model)
