"""
switch_provider.py — Switch between POC (free) and production (paid) mode.
Works on Windows, Mac, and Linux.

Usage (run from the hiring-agent-v2 folder):
    python scripts/switch_provider.py poc
    python scripts/switch_provider.py production
    python scripts/switch_provider.py status
    python scripts/switch_provider.py set-groq   YOUR_KEY
    python scripts/switch_provider.py set-openai YOUR_KEY
    python scripts/switch_provider.py set-apollo YOUR_KEY
"""

import sys
import os
import re
import shutil


# ── Path resolution — works from any working directory ───────────────────────
# Script lives at  <root>/scripts/switch_provider.py
# .env lives at    <root>/.env
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)   # one level up from scripts/
ENV_PATH     = os.path.join(PROJECT_ROOT, ".env")
EXAMPLE_PATH = os.path.join(PROJECT_ROOT, ".env.example")


# ── File I/O with explicit UTF-8 (fixes Windows cp1252 error) ────────────────

def read_env(path=None):
    path = path or ENV_PATH
    if not os.path.exists(path):
        if os.path.exists(EXAMPLE_PATH):
            shutil.copy(EXAMPLE_PATH, path)
            print(f"  Created .env from .env.example at:\n  {path}")
        else:
            return {}
    # encoding="utf-8" + errors="replace" prevents the cp1252 crash on Windows
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    env = {}
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def write_env_key(key, value, path=None):
    path = path or ENV_PATH

    # Create .env if it doesn't exist yet
    if not os.path.exists(path):
        if os.path.exists(EXAMPLE_PATH):
            shutil.copy(EXAMPLE_PATH, path)
        else:
            open(path, "w", encoding="utf-8").close()

    with open(path, encoding="utf-8", errors="replace") as f:
        content = f.read()

    pattern = rf"^{re.escape(key)}\s*=.*$"
    replacement = f"{key}={value}"

    if re.search(pattern, content, re.MULTILINE):
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        content = content.rstrip("\n") + f"\n{key}={value}\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ── Commands ─────────────────────────────────────────────────────────────────

def show_status(env):
    provider = env.get("LLM_PROVIDER", "groq")
    apollo   = env.get("APOLLO_API_KEY", "").strip()
    groq     = env.get("GROQ_API_KEY",   "").strip()
    openai   = env.get("OPENAI_API_KEY", "").strip()

    print()
    print("=" * 50)
    print("  4CECloud AI Hiring Agent — Current Config")
    print("=" * 50)
    print(f"  .env location : {ENV_PATH}")
    print(f"  LLM Provider  : {provider}")
    print(f"  Groq key      : {'YES (free LLM)' if groq   else 'NOT SET'}")
    print(f"  OpenAI key    : {'YES (paid LLM)' if openai else 'NOT SET'}")
    print(f"  Apollo key    : {'YES — live candidate data' if apollo else 'NOT SET — using mock data'}")

    if provider == "groq" and not apollo:
        mode = "POC / FREE  (Groq LLM + mock candidates)"
    elif provider == "openai" and apollo:
        mode = "PRODUCTION  (OpenAI + Apollo live data)"
    else:
        mode = "PARTIAL     (some keys missing)"
    print(f"\n  Mode          : {mode}")
    print("=" * 50)
    print()


def switch_poc():
    write_env_key("LLM_PROVIDER", "groq")
    print("""
Switched to POC mode (Groq free LLM + mock data).

Next steps:
  1. Sign up at https://console.groq.com  (free, 30 seconds)
  2. Create an API key there
  3. Run:
       python scripts/switch_provider.py set-groq  YOUR_GROQ_KEY

  4. Start the backend:
       cd backend
       python -m venv venv
       venv\\Scripts\\activate        (Windows)
       pip install -r requirements.txt
       uvicorn main:app --reload --port 8000

  5. Seed mock candidates (no API needed):
       python scripts/seed_mock.py

  6. Start the frontend (new terminal):
       cd frontend
       npm install
       npm run dev

  Cost: $0.00 / month
""")


def switch_production():
    write_env_key("LLM_PROVIDER", "openai")
    print("""
Switched to production mode (OpenAI + Apollo).

Next steps:
  1. Set OpenAI key:
       python scripts/switch_provider.py set-openai  sk-YOUR_KEY

  2. Set Apollo key:
       python scripts/switch_provider.py set-apollo  YOUR_APOLLO_KEY

  3. Restart the backend.

  Cost: ~$64/month (Apollo $49 + OpenAI ~$15)
""")


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python scripts/switch_provider.py [poc | production | status | set-groq KEY | set-openai KEY | set-apollo KEY]")
        sys.exit(0)

    cmd = args[0].lower()
    env = read_env()

    if cmd == "poc":
        switch_poc()

    elif cmd == "production":
        switch_production()

    elif cmd == "status":
        show_status(env)

    elif cmd == "set-groq" and len(args) > 1:
        write_env_key("GROQ_API_KEY", args[1])
        print(f"  Groq API key saved to {ENV_PATH}")

    elif cmd == "set-gemini" and len(args) > 1:
        write_env_key("GEMINI_API_KEY", args[1])
        write_env_key("LLM_PROVIDER", "gemini")
        print(f"  Gemini API key saved and LLM_PROVIDER set to 'gemini' in {ENV_PATH}")

    elif cmd == "set-openai" and len(args) > 1:
        write_env_key("OPENAI_API_KEY", args[1])
        print(f"  OpenAI API key saved to {ENV_PATH}")

    elif cmd == "set-apollo" and len(args) > 1:
        write_env_key("APOLLO_API_KEY", args[1])
        print(f"  Apollo API key saved to {ENV_PATH}")

    else:
        print(f"  Unknown command: {cmd}")
        print("  Run without arguments to see usage.")


if __name__ == "__main__":
    main()
