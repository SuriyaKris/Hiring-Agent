"""
switch_provider.py — Switch between Gemini (free primary), Groq (free fallback), and OpenAI (production).
Works on Windows, Mac, and Linux.

Usage (run from the hiring-agent-v2 folder):
    python scripts/switch_provider.py gemini
    python scripts/switch_provider.py poc
    python scripts/switch_provider.py production
    python scripts/switch_provider.py status
    python scripts/switch_provider.py set-gemini YOUR_KEY
    python scripts/switch_provider.py set-groq   YOUR_KEY
    python scripts/switch_provider.py set-openai YOUR_KEY
    python scripts/switch_provider.py set-apollo YOUR_KEY
"""

import sys
import os
import re
import shutil


# ── Path resolution — works from any working directory ───────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)   # one level up from scripts/
ENV_PATH     = os.path.join(PROJECT_ROOT, ".env")
BACKEND_ENV_PATH = os.path.join(PROJECT_ROOT, "backend", ".env")
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
    paths = [path] if path else [ENV_PATH, BACKEND_ENV_PATH]
    for target_path in paths:
        if not target_path:
            continue
        if not os.path.exists(target_path):
            if os.path.exists(EXAMPLE_PATH):
                shutil.copy(EXAMPLE_PATH, target_path)
            else:
                open(target_path, "w", encoding="utf-8").close()

        with open(target_path, encoding="utf-8", errors="replace") as f:
            content = f.read()

        pattern = rf"^{re.escape(key)}\s*=.*$"
        replacement = f"{key}={value}"

        if re.search(pattern, content, re.MULTILINE):
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        else:
            content = content.rstrip("\n") + f"\n{key}={value}\n"

        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)


# ── Commands ─────────────────────────────────────────────────────────────────

def show_status(env):
    provider = env.get("LLM_PROVIDER", "gemini")
    gemini   = env.get("GEMINI_API_KEY", "").strip()
    apollo   = env.get("APOLLO_API_KEY", "").strip()
    groq     = env.get("GROQ_API_KEY",   "").strip()
    openai   = env.get("OPENAI_API_KEY", "").strip()

    print()
    print("=" * 55)
    print("  4CECloud AI Hiring Agent — Current Configuration")
    print("=" * 55)
    print(f"  .env location : {ENV_PATH}")
    print(f"  LLM Provider  : {provider.upper()} (Active)")
    print(f"  Gemini key    : {'YES (Primary Free LLM)' if gemini else 'NOT SET'}")
    print(f"  Groq key      : {'YES (Fallback LLM)' if groq else 'NOT SET'}")
    print(f"  OpenAI key    : {'YES (Paid LLM)' if openai else 'NOT SET'}")
    print(f"  Apollo key    : {'YES — live candidate search' if apollo else 'NOT SET — using mock data'}")

    if provider == "gemini" and apollo:
        mode = "RECOMMENDED PRODUCTION (Gemini 3.5 Flash Lite + Apollo Live Search)"
    elif provider == "gemini" and not apollo:
        mode = "GEMINI POC (Gemini 3.5 Flash Lite + Mock Data)"
    elif provider == "groq" and not apollo:
        mode = "GROQ POC (Groq Free LLM + Mock Data)"
    elif provider == "openai" and apollo:
        mode = "PAID PRODUCTION (OpenAI GPT-4o + Apollo Live Search)"
    else:
        mode = "CUSTOM / MIXED"
    print(f"\n  Mode          : {mode}")
    print("=" * 55)
    print()


def switch_gemini():
    write_env_key("LLM_PROVIDER", "gemini")
    print("""
Switched to Gemini mode (Primary Google AI Studio LLM).

Active Models:
  - Fast Model : gemini-3.5-flash-lite
  - Smart Model: gemini-3.5-flash-lite

Next steps:
  1. If you need a key, get one free at: https://aistudio.google.com
  2. Set key with:
       python scripts/switch_provider.py set-gemini YOUR_KEY
  3. Start backend:
       python -m uvicorn main:app --reload --port 8000
""")


def switch_poc():
    write_env_key("LLM_PROVIDER", "groq")
    print("""
Switched to Groq mode (Groq free fallback LLM).

Next steps:
  1. Sign up at https://console.groq.com
  2. Run:
       python scripts/switch_provider.py set-groq YOUR_GROQ_KEY
""")


def switch_production():
    write_env_key("LLM_PROVIDER", "openai")
    print("""
Switched to OpenAI mode (Paid OpenAI + Apollo).

Next steps:
  1. Set OpenAI key:
       python scripts/switch_provider.py set-openai sk-YOUR_KEY
  2. Set Apollo key:
       python scripts/switch_provider.py set-apollo YOUR_APOLLO_KEY
""")


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python scripts/switch_provider.py [gemini | poc | production | status | set-gemini KEY | set-groq KEY | set-openai KEY | set-apollo KEY]")
        sys.exit(0)

    cmd = args[0].lower()
    env = read_env()

    if cmd == "gemini":
        switch_gemini()

    elif cmd == "poc":
        switch_poc()

    elif cmd == "production":
        switch_production()

    elif cmd == "status":
        show_status(env)

    elif cmd == "set-gemini" and len(args) > 1:
        write_env_key("GEMINI_API_KEY", args[1])
        write_env_key("LLM_PROVIDER", "gemini")
        print(f"  Gemini API key saved and LLM_PROVIDER set to 'gemini' in {ENV_PATH} and {BACKEND_ENV_PATH}")

    elif cmd == "set-groq" and len(args) > 1:
        write_env_key("GROQ_API_KEY", args[1])
        print(f"  Groq API key saved to {ENV_PATH} and {BACKEND_ENV_PATH}")

    elif cmd == "set-openai" and len(args) > 1:
        write_env_key("OPENAI_API_KEY", args[1])
        print(f"  OpenAI API key saved to {ENV_PATH} and {BACKEND_ENV_PATH}")

    elif cmd == "set-apollo" and len(args) > 1:
        write_env_key("APOLLO_API_KEY", args[1])
        print(f"  Apollo API key saved to {ENV_PATH} and {BACKEND_ENV_PATH}")

    else:
        print(f"  Unknown command: {cmd}")
        print("  Run without arguments to see usage.")


if __name__ == "__main__":
    main()
