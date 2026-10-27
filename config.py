"""Central configuration for the Smart Agriculture Multi-Agent System."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_BASE_DIR = DATA_DIR / "knowledge_base"
VISION_CHECKPOINT_PATH = BASE_DIR / "vision" / "checkpoints" / "disease_model.pt"

# --- LLM backend ---
LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama").lower()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# MLX-LM is used only by the optional E3 Apple-Silicon deployment-backend
# experiment.  A local, explicitly bound model directory is required; unlike
# Ollama, no model is selected implicitly by a tag.
MLX_MODEL_PATH = os.getenv("MLX_MODEL_PATH", "")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# --- LLM call resilience ---
# Long evaluation runs (many scenarios x 4 systems) make many LLM calls; a single transient
# network timeout shouldn't crash the whole run. generate() retries with exponential backoff
# before giving up on a call.
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "4"))
LLM_RETRY_BACKOFF_BASE_S = float(os.getenv("LLM_RETRY_BACKOFF_BASE_S", "3"))

# --- Provenance-constrained benchmark LLM boundary ---
# The benchmark remains offline/deterministic by default so source-audit tests
# never require a running model. Set BENCHMARK_LLM_ENABLED=true for the eight
# bounded interpretation/explanation calls. These calls can select only
# already-admitted fact IDs; they cannot change a gate, action, source, or
# citation. Set REQUIRED=true for experimental runs that must fail if a model
# backend is unavailable instead of recording a deterministic safe fallback.
BENCHMARK_LLM_ENABLED = os.getenv("BENCHMARK_LLM_ENABLED", "false").lower() in {
    "1", "true", "yes", "on"
}
BENCHMARK_LLM_REQUIRED = os.getenv("BENCHMARK_LLM_REQUIRED", "false").lower() in {
    "1", "true", "yes", "on"
}
BENCHMARK_LLM_MAX_SELECTED_FACTS = int(
    os.getenv("BENCHMARK_LLM_MAX_SELECTED_FACTS", "3")
)

# --- RAG ---
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "500"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "80"))

# --- Coordinator ---
CONFLICT_SIMILARITY_THRESHOLD = 0.35  # below this, agent recommendations are considered "conflicting"
DEFAULT_CONFIDENCE_IF_NO_CONFLICT = 0.85
DEFAULT_CONFIDENCE_IF_CONFLICT = 0.6

# --- Weather ---
WEATHER_PROVIDER = os.getenv("WEATHER_PROVIDER", "open-meteo")

# --- Market (USDA NASS) ---
NASS_API_KEY = os.getenv("NASS_API_KEY", "")
NASS_COMMODITY = os.getenv("NASS_COMMODITY", "") or None  # no default crop — must be set explicitly
NASS_STATE = os.getenv("NASS_STATE", "") or None

# --- Market (India data.gov.in / AGMARKNET) ---
DATA_GOV_IN_API_KEY = os.getenv("DATA_GOV_IN_API_KEY", "")
DATA_GOV_MARKET_RESOURCE_ID = os.getenv(
    "DATA_GOV_MARKET_RESOURCE_ID",
    "9ef84268-d588-465a-a308-a864a43d0070",
)
