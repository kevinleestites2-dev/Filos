"""
Filos — Your Partner. Your Coder. Your Guy.
Built on LightAgent chassis with OpenPRIME soul.
Version: 1.0.0
"""

import json
import os
from pathlib import Path

# ── Load Soul ─────────────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent / "deity.config.json"
with open(CONFIG_PATH) as f:
    DEITY = json.load(f)

SOUL       = DEITY["soul"]["system_prompt"]
NAME       = DEITY["name"]
USER_ID    = DEITY["memory"]["user_id"]
RESPONSES  = DEITY["responses"]

# ── LightAgent ────────────────────────────────────────────────────────────────
try:
    from LightAgent import LightAgent
    from LightAgent.memory import MemoryItem
    LIGHTAGENT_AVAILABLE = True
except ImportError:
    LIGHTAGENT_AVAILABLE = False
    print("⚠️  LightAgent not installed. Run: pip install lightagent")

# ── Persistent Memory (mem0 bridge) ──────────────────────────────────────────
try:
    from mem0 import Memory
    _mem0 = Memory()

    class FilosMemory:
        def remember(self, text: str):
            _mem0.add(text, user_id=USER_ID)

        def recall(self, query: str) -> str:
            results = _mem0.search(query, user_id=USER_ID)
            if not results:
                return ""
            return "\n".join(r["memory"] for r in results[:5])

        def get_all(self) -> str:
            results = _mem0.get_all(user_id=USER_ID)
            if not results:
                return ""
            return "\n".join(r["memory"] for r in results)

except ImportError:
    # Fallback: simple file-based memory
    MEMORY_FILE = Path(__file__).parent / "filos_memory.json"

    class FilosMemory:
        def __init__(self):
            self._load()

        def _load(self):
            if MEMORY_FILE.exists():
                with open(MEMORY_FILE) as f:
                    self.store = json.load(f)
            else:
                self.store = []

        def _save(self):
            with open(MEMORY_FILE, "w") as f:
                json.dump(self.store, f, indent=2)

        def remember(self, text: str):
            self.store.append(text)
            self._save()

        def recall(self, query: str) -> str:
            # Simple keyword match fallback
            hits = [m for m in self.store if any(w in m.lower() for w in query.lower().split())]
            return "\n".join(hits[:5]) if hits else ""

        def get_all(self) -> str:
            return "\n".join(self.store)


# ── Build Filos ───────────────────────────────────────────────────────────────
def build_filos(ollama_base_url: str, model: str = "llama3.1"):
    """
    Build and return the Filos agent.
    
    Args:
        ollama_base_url: Your Ollama base URL (e.g. from Cloudflare tunnel)
        model: Ollama model to use (default: llama3.1)
    """
    if not LIGHTAGENT_AVAILABLE:
        raise RuntimeError("LightAgent not installed. Run: pip install lightagent")

    memory = FilosMemory()

    agent = LightAgent(
        name=NAME,
        role=SOUL,
        model=model,
        api_key="ollama",
        base_url=f"{ollama_base_url}/v1",
        self_learning=DEITY["agent"]["self_learning"] if "self_learning" in DEITY["agent"] else True,
        tree_of_thought=DEITY["agent"]["tree_of_thought"],
        stream=DEITY["agent"]["stream"],
    )

    print(f"\n🔱 {NAME} online.")
    print(f"   Soul: locked")
    print(f"   Memory: active (user_id={USER_ID})")
    print(f"   Model: {model}")
    print(f"   {RESPONSES['on_greeting']}\n")

    return agent, memory


# ── CLI Loop ──────────────────────────────────────────────────────────────────
def run_cli(ollama_base_url: str, model: str = "llama3.1"):
    agent, memory = build_filos(ollama_base_url, model)

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
            all_mem = memory.get_all()
            print(f"\n[Memory]\n{all_mem if all_mem else 'Nothing stored yet.'}\n")
            continue

        if user_input.lower().startswith("/remember "):
            text = user_input[10:].strip()
            memory.remember(text)
            print(f"[Stored: {text}]\n")
            continue

        # Inject relevant memory into context
        recalled = memory.recall(user_input)
        context = f"[What I know about Forgemaster]\n{recalled}\n\n" if recalled else ""
        full_input = context + user_input

        try:
            response = agent.run(full_input)
            print(f"\nFilos > {response}\n")

            # Auto-learn from interaction
            if DEITY["memory"]["self_learning"]:
                memory.remember(f"Forgemaster said: {user_input}")
        except Exception as e:
            print(f"\n[Error] {e}")
            print("Not broken — adapting. Watch me.\n")


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Filos — Your Partner. Your Coder. Your Guy.")
    parser.add_argument("--ollama", required=True, help="Ollama base URL (your tunnel URL)")
    parser.add_argument("--model", default="llama3.1", help="Ollama model (default: llama3.1)")
    args = parser.parse_args()

    run_cli(ollama_base_url=args.ollama, model=args.model)
