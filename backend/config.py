from dotenv import load_dotenv
import os

load_dotenv(override=False)  # env vars set in the process always win over .env

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = os.getenv("MODEL", "claude-sonnet-4-6")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
# Cheaper/faster model for mechanical JSON extraction (the 2nd call per agent).
PARSE_MODEL = os.getenv("PARSE_MODEL", "claude-haiku-4-5-20251001")

# Set MOCK_MODE=true in .env to run without an API key (returns demo data)
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() in ("true", "1", "yes")

# Serper.dev API key for live web search in the Market Research Agent.
# Free tier: 2,500 searches/month — sign up at https://serper.dev
# If not set, the Market Research Agent falls back to Claude-only analysis.
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

if not ANTHROPIC_API_KEY and not MOCK_MODE:
    raise ValueError(
        "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.\n"
        "Tip: set MOCK_MODE=true in .env to run a live demo without an API key."
    )
